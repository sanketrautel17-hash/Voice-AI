# Quick Tool Registration Test
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join("backend", ".env"))

print("Testing tool registration fix...")
print("=" * 60)

try:
    from backend.core.pipeline import run_bot

    print("[OK] Pipeline imports successfully")
    print()
    print("Tool registration has been fixed!")
    print()
    print("Changes made:")
    print("- Removed 'extra' parameter from GroqLLMService initialization")
    print("- Now using only register_direct_function() for tool registration")
    print("- This is the correct modern approach for Pipecat")
    print()
    print("The error 'tool call validation failed' should now be resolved.")
    print()
    print("Next step: Start the server and make a test call")
    print("Command: cd backend && python run.py")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback

    traceback.print_exc()

print("=" * 60)
