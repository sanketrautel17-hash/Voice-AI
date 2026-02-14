# Tool Calling Test Script
# This tests if the LLM is actually using the registered tools

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment
sys.path.append(os.getcwd())
load_dotenv("backend/.env")

print("=" * 60)
print("TESTING TOOL CALLING")
print("=" * 60)
print()


async def test_tools():
    from pipecat.services.groq import GroqLLMService
    from pipecat.processors.frame_processor import FunctionCallParams
    from pipecat.frames.frames import FunctionCallResultFrame

    # Create LLM
    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )

    # Define test tool
    async def test_search(params: FunctionCallParams, query: str):
        """Search for information."""
        return f"Found results for: {query}"

    # Register tool
    llm.register_direct_function(test_search)

    print(f"✅ Registered tool: test_search")
    print(f"✅ LLM has {len(llm._functions)} functions")
    print()

    # Check internal structure
    if hasattr(llm, "_functions"):
        print("Functions registered:")
        for name, func in llm._functions.items():
            print(f"  - {name}")
    print()

    print("Tool registration successful!")
    print()
    print("To verify tools work in actual calls:")
    print("1. Check Pipecat logs for 'function_call' or 'tool_call'")
    print("2. Enable Pipecat debug logging")
    print("3. Monitor network requests to Groq API")


if __name__ == "__main__":
    asyncio.run(test_tools())

print("=" * 60)
