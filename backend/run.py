import uvicorn
import asyncio
import sys
import os

if __name__ == "__main__":
    # Set the event loop policy for Windows specifically to avoid "Event loop is closed"
    # and connection timeouts with some asyncio libraries (like Deepgram/websockets)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("Windows Event Loop Policy set to SelectorEventLoopPolicy")

    # Run the uvicorn server programmatically
    # equivalent to: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    print(f"Running with python: {sys.executable}")
    # Import app directly to avoid string import issues if paths are weird
    from main import app

    uvicorn.run(app, host="0.0.0.0", port=8000)
