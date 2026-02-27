import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from commons.logger import logger
from core.db.database import get_database

# Pipecat imports
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
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

# Core imports (Refactored)
from core.prompts.system import SYSTEM_PROMPT
from core.processors.frame_processors import GoodbyeDetector
from core.tools.manager import ToolManager
from core.services.analytics import analyze_call_transcript

log = logger(__name__)
load_dotenv()


async def run_bot(transport, stream_sid, call_sid):
    # 1. Services
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # llama-3.3-70b-versatile: best Groq model for tool calling that
    # correctly respects tool_choice="none" during non-tool phases.
    # openai/gpt-oss-120b was crashing because it called tools even when
    # tool_choice was set to "none" (e.g. during the intro greeting).
    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )

    # 2. Context (Memory)
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
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

    # 4. Initialize Components (Tools & Processors)
    # Create GoodbyeDetector
    goodbye_detector = GoodbyeDetector()

    # Create ToolManager
    tool_manager = ToolManager(task=None, call_sid=call_sid)

    # 5. Pipeline Structure
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            goodbye_detector,  # Intercepts transcriptions
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    # 6. Task
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

    # Wired up dependencies
    goodbye_detector.set_task(task)
    tool_manager.task = task

    # Register Tools with LLM
    tools = [
        tool_manager.get_loan_information,
        tool_manager.search_web,
        tool_manager.end_call,
    ]

    log.info(f"🔧 Registering {len(tools)} tools with LLM...")
    log.info("=" * 60)
    for tool in tools:
        llm.register_direct_function(tool)
        log.info(f"  ✓ Registered: {tool.__name__}")
        log.info(f"    Docstring: {tool.__doc__[:100] if tool.__doc__ else 'None'}...")
        # Log function signature
        import inspect

        sig = inspect.signature(tool)
        log.info(f"    Signature: {tool.__name__}{sig}")
    log.info("=" * 60)

    runner = PipelineRunner()

    # 7. Lifecycle Handlers
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        try:
            log.info("🔌 Transport connected. Starting call...")
            await asyncio.sleep(2.0)
            await task.queue_frames(
                [
                    TextFrame(
                        text="Hello! I'm FinBot. How can I assist you with your loan inquiry today?"
                    )
                ]
            )
        except Exception as e:
            log.error(f"❌ Error in on_client_connected: {e}")

    # --- DB: Save Call Start ---
    db = get_database()
    if db is not None:
        await db["calls"].insert_one(
            {
                "call_sid": call_sid,
                "stream_sid": stream_sid,
                "status": "started",
                "start_time": datetime.utcnow(),
            }
        )

    try:
        log.info(f"▶️ Running pipeline task for call_sid: {call_sid}")
        await runner.run(task)
    except Exception as e:
        log.error(f"❌ Pipeline execution failed: {e}")

    # --- Post-Call Analysis ---
    # Serialize history
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

    log.info("📊 Analyzing call...")
    analysis_result = await analyze_call_transcript(serializable_history)
    log.info(f"Analysis result: {analysis_result}")

    if db is not None:
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

        if analysis_result.get("is_interested"):
            log.info("💰 User showed interest - saving to loan_interests collection")
            await db["loan_interests"].insert_one(
                {
                    "call_sid": call_sid,
                    "analysis": analysis_result,
                    "timestamp": datetime.utcnow(),
                }
            )


async def bot(websocket, stream_sid, call_sid):
    try:
        serializer = TwilioFrameSerializer(
            stream_sid=stream_sid,
            call_sid=call_sid,
            account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        )

        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                serializer=serializer,
            ),
        )

        await run_bot(transport, stream_sid, call_sid)
    except Exception as e:
        log.error(f"❌ Error in bot function: {e}")
