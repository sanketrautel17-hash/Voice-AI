import asyncio
import os
from dotenv import load_dotenv
from deepgram import DeepgramClient, SpeakOptions

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


async def test_deepgram_tts():
    try:
        print(f"Testing Deepgram with Key: {DEEPGRAM_API_KEY[:5]}...")
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        options = SpeakOptions(
            model="aura-asteria-en",
        )

        filename = "test_output.mp3"
        print("Sending TTS request...")
        response = deepgram.speak.rest.v("1").save(
            filename, {"text": "Hello, this is a test."}, options
        )
        print(f"TTS Successful! Saved to {filename}")

    except Exception as e:
        print(f"Deepgram Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_deepgram_tts())
