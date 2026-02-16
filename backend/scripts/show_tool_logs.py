import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add backend root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
sys.path.append(backend_root)

# Load env from backend root
load_dotenv(os.path.join(backend_root, ".env"))

from core.db.database import get_database, connect_to_mongo


async def show_logs():
    await connect_to_mongo()
    db = get_database()

    print("=" * 60)
    print("RECENT TOOL EXECUTIONS (From MongoDB)")
    print("=" * 60)

    cursor = db.tool_logs.find().sort("timestamp", -1).limit(10)
    logs = await cursor.to_list(length=10)

    if not logs:
        print("No tool logs found yet.")
    else:
        for log in logs:
            time_str = log.get("timestamp", datetime.now()).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            tool = log.get("tool", "Unknown")
            query = log.get("query", "N/A")
            result = log.get("result", "No result")

            print(f"[{time_str}] Tool: {tool}")
            print(f"  Query: {query}")
            print(
                f"  Result: {result[:200]}..."
                if len(result) > 200
                else f"  Result: {result}"
            )
            print("-" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(show_logs())
