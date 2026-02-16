import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

# Mock logging to avoid needing the actual logger setup
mock_log = Mock()


# Mock pipecat classes
class FunctionCallParams:
    pass


class TextFrame:
    def __init__(self, text):
        self.text = text


class EndFrame:
    pass


# Simplified task mock
mock_task = AsyncMock()


# The logic to test (copied from the fixed pipeline.py)
async def log_tool_usage(tool_name, query, result):
    # Mock implementation
    pass


async def end_call(params: FunctionCallParams, **kwargs):
    """
    End the conversation and disconnect the call.
    Use this when the user says goodbye or when the conversation has come to a natural conclusion.
    """
    mock_log.info("end_call tool invoked. Sending goodbye and hanging up...")
    if kwargs:
        mock_log.info(f"end_call received unexpected kwargs: {kwargs}")

    await log_tool_usage("end_call", "N/A", "Call termination requested")
    try:
        # Send a goodbye message before ending
        await mock_task.queue_frames(
            [
                TextFrame(text="Thank you for your time. Have a great day! Goodbye."),
            ]
        )
        # Small delay to allow the goodbye message to be spoken
        # await asyncio.sleep(1.5) # Commented out for test speed
        # Now send the EndFrame to terminate
        await mock_task.queue_frames([EndFrame()])
        mock_log.info("EndFrame queued. Call should terminate.")
    except Exception as e:
        mock_log.error(f"Error in end_call: {e}")
    return "Call ended successfully."


class TestEndCall(unittest.IsolatedAsyncioTestCase):
    async def test_end_call_with_kwargs(self):
        print("Testing end_call with extra arguments (simulating LLM hallucination)...")
        params = FunctionCallParams()

        # This call would previously fail with TypeError
        try:
            result = await end_call(
                params, reason="user said goodbye", other_junk="123"
            )
            print(f"Result: {result}")
        except TypeError as e:
            self.fail(f"end_call crashed with TypeError: {e}")

        # Verify kwargs were logged
        mock_log.info.assert_any_call(
            "end_call received unexpected kwargs: {'reason': 'user said goodbye', 'other_junk': '123'}"
        )

        # Verify frames were queued
        self.assertEqual(mock_task.queue_frames.call_count, 2)
        # Check first call (Goodbye text)
        args1, _ = mock_task.queue_frames.call_args_list[0]
        self.assertIsInstance(args1[0][0], TextFrame)
        # Check second call (EndFrame)
        args2, _ = mock_task.queue_frames.call_args_list[1]
        self.assertIsInstance(args2[0][0], EndFrame)

        print(
            "SUCCESS: end_call handled extra arguments correctly and queued EndFrame."
        )


if __name__ == "__main__":
    unittest.main()
