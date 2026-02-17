"""
Test script to verify tool registration with Groq LLM
"""

import sys
import os
import asyncio

sys.path.append(os.path.join(os.getcwd(), "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join("backend", ".env"))

print("=" * 70)
print("TESTING TOOL REGISTRATION")
print("=" * 70)
print()

# Import the ToolManager
from backend.core.tools.manager import ToolManager
from pipecat.services.groq.llm import GroqLLMService

print("[1] Creating ToolManager...")
tool_manager = ToolManager(task=None, call_sid="test_sid")
print("    ✓ ToolManager created")
print()

print("[2] Creating Groq LLM Service...")
llm = GroqLLMService(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
)
print("    ✓ LLM Service created")
print()

print("[3] Registering tools...")
tools = [
    tool_manager.get_loan_information,
    tool_manager.search_web,
    tool_manager.end_call,
]

import inspect

for tool in tools:
    print(f"\n  Tool: {tool.__name__}")
    print(f"  Signature: {inspect.signature(tool)}")
    print(f"  Docstring preview: {tool.__doc__[:150] if tool.__doc__ else 'None'}...")

    # Register the tool
    try:
        llm.register_direct_function(tool)
        print(f"  ✅ Registration successful!")
    except Exception as e:
        print(f"  ❌ Registration failed: {e}")

print()
print("=" * 70)

# Check if LLM has tools registered
if hasattr(llm, "_functions") or hasattr(llm, "functions"):
    functions = getattr(llm, "_functions", None) or getattr(llm, "functions", None)
    print(f"\n[4] LLM now has {len(functions) if functions else 0} tools registered")
    if functions:
        for func_name in functions:
            print(f"    - {func_name}")
else:
    print("\n[4] Cannot introspect LLM functions (may be private)")

print()
print("=" * 70)
print("✅ TEST COMPLETE")
print()
print("Next steps:")
print("1. Run the backend server: cd backend && python run.py")
print("2. Make a test call and ask about loan rates")
print("3. Check backend/logs/debug.log for tool call logs")
print("=" * 70)
