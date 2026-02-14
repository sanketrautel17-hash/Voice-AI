import os
import sys
import asyncio
from datetime import datetime
import json
from commons.logger import logger

log = logger(__name__)
from groq import AsyncGroq

from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.frames.frames import TextFrame, EndFrame
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

from core.db.database import get_database


from core.rag.knowledge_base import kb
from core.tools.web_search import web_searchER


from pipecat.services.llm_service import FunctionCallParams


async def run_bot(transport, stream_sid, call_sid):
    # 1. Services
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # Using Groq LLM Service with explicit tool configuration
    from pipecat.services.openai.base_llm import BaseOpenAILLMService

    # Define tools in OpenAI format
    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_loan_information",
                "description": "Search the bank's internal knowledge base for loan policies, interest rates, and documents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query (e.g., 'home loan interest rates').",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the public web for current market rates, competitor info, or general financial news.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query (e.g., 'current prime rate').",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "end_call",
                "description": "End the conversation and disconnect the call. Use this when the user says goodbye or when the conversation has come to a natural conclusion.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )

    # 2. Context (Memory)
    messages = [
        {
            "role": "system",
            "content": """You are FinBot, a helpful bank loan assistant.

⚠️ YOU MUST USE TOOLS - Never answer without checking tools first!

═══════════════════════════════
🔧 TOOL USAGE (MANDATORY):
═══════════════════════════════

❗❗❗ MOST IMPORTANT - ENDING CALLS ❗❗❗
3️⃣ When user says ANY of these words:
   - goodbye, bye, thanks, thank you
   - that's all, I'm done, no more questions
   - not interested, no thanks
   
   → YOU MUST IMMEDIATELY call end_call()
   → DO NOT just say goodbye
   → DO NOT continue conversation  
   → CALL THE FUNCTION: end_call()

1️⃣ When user asks about RATES/LOANS:
   → ALWAYS call get_loan_information(query="user question here")
   → If no info found, THEN call search_web(query="specific search")

2️⃣ When user asks about RBI/MARKET rates:
   → IMMEDIATELY call search_web(query="RBI home loan rate 2026")

═══════════════════════════════
📝 EXAMPLES:
═══════════════════════════════

User: "What's your home loan rate?"
You: [CALL get_loan_information(query="home loan interest rate")]
Then respond with the result.

User: "What's the RBI rate?"
You: [CALL search_web(query="current RBI home loan interest rate India 2026")]
Then share the findings.

User: "Thanks, goodbye!"
You: [CALL end_call()]  ← MANDATORY! DO THIS!

User: "That's all I needed"
You: [CALL end_call()]  ← MANDATORY! DO THIS!

User: "Not interested"
You: [CALL end_call()]  ← MANDATORY! DO THIS!

═══════════════════════════════
⚡ REMEMBER:
═══════════════════════════════
- STEP 1: Use tool
- STEP 2: Share result  
- STEP 3: Ask if they need more help
- On goodbye/thanks/bye: IMMEDIATELY CALL end_call()

Be brief (1-2 sentences). Be helpful. USE YOUR TOOLS!""",
        }
    ]

    context = LLMContext(messages)

    # 3. Aggregators with VAD and Turn Strategy
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                stop=[
                    TurnAnalyzerUserTurnStopStrategy(
                        turn_analyzer=LocalSmartTurnAnalyzerV3()
                    )
                ]
            ),
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        ),
    )

    # 4. Pipeline Structure
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    # 5. Task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
        ),
    )

    # Tool Logging Helper
    async def log_tool_usage(tool_name: str, query: str, result: str):
        try:
            log.info(f"EXECUTING TOOL: {tool_name} | Query: {query}")
            db_instance = get_database()  # Use imported function
            if db_instance is not None:
                log_entry = {
                    "call_sid": call_sid,
                    "tool": tool_name,
                    "query": query,
                    "result": str(result),
                    "timestamp": datetime.now(),
                }
                # Use insert_one correctly on the collection
                await db_instance["tool_logs"].insert_one(log_entry)
                log.info(f"TOOL RESULT LOGGED: {str(result)[:100]}...")
            else:
                log.warning("Database instance not available for logging tool usage")
        except Exception as e:
            log.error(f"Failed to log tool usage: {e}")

    # Tool Definitions (Defined here so they can access 'task')
    async def get_loan_information(params: FunctionCallParams, query: str):
        """
        Search the bank's internal knowledge base for loan policies, interest rates, and documents.
        Args:
            query (str): The search query (e.g., "home loan interest rates").
        """
        log.info(f"get_loan_information called with query: {query}")
        result = await asyncio.to_thread(kb.query, query)
        await log_tool_usage("get_loan_information", query, result)
        return result

    async def search_web(params: FunctionCallParams, query: str):
        """
        Search the public web for current market rates, competitor info, or general financial news.
        Args:
            query (str): The search query (e.g., "current prime rate").
        """
        log.info(f"search_web called with query: {query}")
        result = await asyncio.to_thread(web_searchER.search, query)
        await log_tool_usage("search_web", query, result)
        return result

    async def end_call(params: FunctionCallParams):
        """
        End the conversation and disconnect the call.
        Use this when the user says goodbye or when the conversation has come to a natural conclusion.
        """
        log.info("end_call tool invoked. Sending goodbye and hanging up...")
        await log_tool_usage("end_call", "N/A", "Call termination requested")
        try:
            # Send a goodbye message before ending
            await task.queue_frames(
                [
                    TextFrame(
                        text="Thank you for your time. Have a great day! Goodbye."
                    ),
                ]
            )
            # Small delay to allow the goodbye message to be spoken
            await asyncio.sleep(1.5)
            # Now send the EndFrame to terminate
            await task.queue_frames([EndFrame()])
            log.info("EndFrame queued. Call should terminate.")
        except Exception as e:
            log.error(f"Error in end_call: {e}")
        return "Call ended successfully."

    start_func = lambda params: None  # Helper for list

    tools = [get_loan_information, search_web, end_call]

    # Register tools
    log.info(f"Registering {len(tools)} tools: {[t.__name__ for t in tools]}")
    for tool in tools:
        llm.register_direct_function(tool)
        log.info(f"✓ Registered: {tool.__name__}")

    log.info(f"LLM has {len(llm._functions)} functions registered")

    runner = PipelineRunner()

    # 6. Lifecycle Handlers
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        try:
            log.info("Transport connected. Starting outbound call conversation...")
            # Inject greeting with a delay to ensure audio path is ready
            await asyncio.sleep(2.0)
            await task.queue_frames(
                [
                    TextFrame(
                        text="Please introduce yourself and start the conversation."
                    )
                ]
            )
        except Exception as e:
            log.error(f"Error in on_client_connected: {e}")

    # --- DB: Save Call Start ---
    db = get_database()
    await db["calls"].insert_one(
        {
            "call_sid": call_sid,
            "stream_sid": stream_sid,
            "status": "started",
            "start_time": datetime.utcnow(),
        }
    )

    try:
        log.info(f"Running pipeline task for call_sid: {call_sid}")
        await runner.run(task)
    except Exception as e:
        log.error(f"Pipeline execution failed: {e}")

    # --- DB: Save Call End & Transcript ---
    def serialize_frame_data(data):
        if isinstance(data, dict):
            return {k: serialize_frame_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [serialize_frame_data(item) for item in data]
        elif hasattr(data, "isoformat"):
            return data.isoformat()
        elif hasattr(data, "__dict__"):
            return serialize_frame_data(data.__dict__)
        elif hasattr(data, "text") and hasattr(data, "parts"):
            return str(data)
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            return str(data)

    serializable_history = [serialize_frame_data(msg) for msg in context.messages]

    # --- Post-Call Analysis ---
    async def analyze_call(transcript_data):
        try:
            # Simple prompt for analysis
            analysis_prompt = f"""
            Analyze the following sales call transcript between an AI assistant and a user.
            Determine if the user is interested in a loan.
            
            Transcript: {str(transcript_data)[:10000]}  # Truncate if too long
            
            Return a valid JSON object with these fields:
            - is_interested: boolean (true/false)
            - loan_type: string (e.g., "Home", "Personal", "Auto", or "None")
            - lead_score: integer (1-10, where 10 is highly interested)
            - summary: string (brief summary of the conversation)
            - next_step: string (what should happen next?)
            
            Do not include any markdown formatting (like ```json). Just the JSON string.
            """

            # Initialize AsyncGroq client
            client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

            completion = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": analysis_prompt}],
                response_format={"type": "json_object"},
            )

            text = completion.choices[0].message.content

            # Clean up response text to ensure it's valid JSON
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]

            return json.loads(text)
        except Exception as e:
            log.error(f"Failed to analyze call: {e}")
            return {"error": str(e), "is_interested": False}

    # Perform analysis
    analysis_result = await analyze_call(serializable_history)

    await db["calls"].update_one(
        {"call_sid": call_sid},
        {
            "$set": {
                "status": "completed",
                "end_time": datetime.utcnow(),
                "transcript": serializable_history,
                "analysis": analysis_result,
            }
        },
    )

    # Save to loan_interests collection as per plan
    if analysis_result.get("is_interested"):
        await db["loan_interests"].insert_one(
            {
                "call_sid": call_sid,
                "analysis": analysis_result,
                "timestamp": datetime.utcnow(),
            }
        )


async def bot(websocket, stream_sid, call_sid):
    try:
        # Initialize Transport
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                serializer=TwilioFrameSerializer(
                    stream_sid=stream_sid,
                    call_sid=call_sid,
                    account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
                    auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
                ),
            ),
        )

        await run_bot(transport, stream_sid, call_sid)
    except Exception as e:
        log.error(f"Error in bot function: {e}")
