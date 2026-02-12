import asyncio
import os
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


async def test_deepgram_ws():
    print(f"Testing Deepgram WebSocket with Key: {DEEPGRAM_API_KEY[:5]}...")

    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        # Create a websocket connection to Deepgram
        dg_connection = deepgram.listen.asyncwebsocket.v("1")

        def on_open(self, open, **kwargs):
            print(f"Connection Open: {open}")

        def on_message(self, result, **kwargs):
            print(f"Message Received: {result}")

        def on_close(self, close, **kwargs):
            print(f"Connection Closed: {close}")

        def on_error(self, error, **kwargs):
            print(f"Error Received: {error}")

        dg_connection.on(LiveTranscriptionEvents.Open, on_open)
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Close, on_close)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
        )

        print("Connecting to Deepgram WebSocket...")
        if await dg_connection.start(options):
            print("Connected to Deepgram WebSocket successfully!")
            await asyncio.sleep(5)  # Keep open for a bit
            await dg_connection.finish()
            print("Finished successfully.")
        else:
            print("Failed to start connection.")

    except Exception as e:
        print(f"Deepgram WebSocket Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_deepgram_ws())
