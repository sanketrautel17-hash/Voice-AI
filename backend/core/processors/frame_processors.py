import re
import asyncio
from pipecat.frames.frames import TextFrame, EndFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameProcessor
from commons.logger import logger

log = logger(__name__)


class GoodbyeDetector(FrameProcessor):
    """Detects goodbye phrases and automatically terminates the call."""

    GOODBYE_PATTERNS = [
        r"\b(goodbye|bye|good bye|bye bye)\b",
        r"\b(thanks|thank you|thankyou)\s*(bye|goodbye)?\b",
        r"\b(that\'s all|thats all|i\'m done|im done)\b",
        r"\b(not interested|no thanks|no thank you)\b",
        r"\b(have a good day|take care)\b",
        r"\b(see you|talk to you later|ttyl)\b",
    ]

    def __init__(self, task=None, **kwargs):
        super().__init__(**kwargs)
        self.task = task
        self.call_ended = False
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.GOODBYE_PATTERNS
        ]

    def set_task(self, task):
        self.task = task

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)

        # Only check transcription frames from the user
        if isinstance(frame, TranscriptionFrame) and not self.call_ended:
            text = frame.text.lower().strip()
            log.info(f"🎤 User said: {text}")

            # Check if any goodbye pattern matches
            for pattern in self.compiled_patterns:
                if pattern.search(text):
                    log.info(
                        f"🛑 GOODBYE DETECTED: '{text}' - Terminating call immediately!"
                    )

                    if not self.task:
                        log.warning(
                            "⚠️ GoodbyeDetector detected goodbye but 'task' is not set!"
                        )
                        break

                    self.call_ended = True

                    # Queue goodbye message and end frame
                    await self.task.queue_frames(
                        [
                            TextFrame(
                                text="Thank you for your time. Have a great day! Goodbye."
                            ),
                        ]
                    )

                    # Wait for goodbye to be spoken
                    await asyncio.sleep(1.5)

                    # Send EndFrame to terminate
                    await self.task.queue_frames([EndFrame()])
                    log.info("✅ Call termination initiated via GoodbyeDetector")
                    break

        # Pass the frame along the pipeline
        await self.push_frame(frame, direction)
