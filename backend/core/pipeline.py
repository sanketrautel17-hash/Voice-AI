import os
import sys
import asyncio
from datetime import datetime
import json
from loguru import logger

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
from pipecat.frames.frames import TextFrame
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

from core.db.database import get_database


async def run_bot(transport, stream_sid, call_sid):
    # 1. Services
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # Using Gemini 1.5 Flash (Stable, higher quota)
    # DO NOT use 2.0-flash or 2.5-flash as they have very low daily limits (20 req/day)
    llm = GoogleLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-3-flash-preview"
    )

    # 2. Context (Memory)
    messages = [
        {
            "role": "system",
            "content": """You are a helpful and professional bank loan assistant called 'FinBot'. 
            Your goal is to determine if the user is interested in a loan.
            
            Start by introducing yourself and asking how you can help.
            If the user mentions loans, ask them what kind of loan they are looking for (e.g., Home, Personal, Auto).
            Finally, ask a few qualifying questions to gauge their interest level.
            At the end of the conversation, thank them.
            
            Keep your responses short and conversational.""",
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

    runner = PipelineRunner()

    # 6. Lifecycle Handlers
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Transport connected. Starting outbound call conversation...")
        # Inject greeting with a delay to ensure audio path is ready
        await asyncio.sleep(2.0)
        await task.queue_frames(
            [TextFrame(text="Please introduce yourself and start the conversation.")]
        )

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
        await runner.run(task)
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")

    # --- DB: Save Call End & Transcript ---
    def serialize_frame_data(data):
        if isinstance(data, dict):
            return {k: serialize_frame_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [serialize_frame_data(item) for item in data]
        elif hasattr(data, "iso_format"):
            return data.iso_format()
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

            # Using the existing LLM service's underlying model or client if accessible,
            # or just quick generation via a new request.
            # Since LLMService in Pipecat wraps the engine,
            # we might need to use the `google.genai` client directly for a one-off completion
            # OR use the service if it exposes a 'generate' method. Ref: GoogleLLMService might not expose raw generate easily.
            # Let's instantiate a fresh lightweight client for this control task or use the configured one.
            import google.generativeai as genai

            # Configure directly for this utility task
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash-001")  # Use stable model
            response = await model.generate_content_async(analysis_prompt)

            # Clean up response text to ensure it's valid JSON
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]

            return json.loads(text)
        except Exception as e:
            logger.error(f"Failed to analyze call: {e}")
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
