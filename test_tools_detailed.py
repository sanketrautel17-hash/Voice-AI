# -*- coding: utf-8 -*-
"""
Detailed tool testing script for Voice AI project
Tests each component individually with better error reporting
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load environment variables
load_dotenv(os.path.join("backend", ".env"))

print("=" * 60)
print("VOICE AI - DETAILED TOOL TESTING")
print("=" * 60)
print()

# Test 1: Environment Variables
print("[Test 1] Checking Environment Variables...")
print("-" * 60)
required_vars = ["MONGODB_URL", "GOOGLE_API_KEY", "TAVILY_API_KEY", "GROQ_API_KEY"]

env_status = True
for var in required_vars:
    value = os.getenv(var)
    if value:
        # Mask the actual value for security
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"[OK] {var}: {masked}")
    else:
        print(f"[FAIL] {var}: NOT SET")
        env_status = False

print()
if not env_status:
    print("WARNING: Some environment variables are missing!")
    print("   Please check your backend/.env file")
    sys.exit(1)

# Test 2: MongoDB Connection
print("[Test 2] Testing MongoDB Connection...")
print("-" * 60)
try:
    from backend.core.db.database import (
        connect_to_mongo,
        close_mongo_connection,
        get_database,
    )

    async def test_mongo():
        try:
            await connect_to_mongo()
            db = get_database()
            # Try to ping
            await db.command("ping")
            print("[OK] MongoDB connection successful!")
            print(f"   Database: voice_project")

            # List collections
            collections = await db.list_collection_names()
            print(
                f"   Collections: {collections if collections else 'None (empty database)'}"
            )

            await close_mongo_connection()
            return True
        except Exception as e:
            print(f"[FAIL] MongoDB connection failed: {str(e)}")
            return False

    mongo_ok = asyncio.run(test_mongo())
    print()
except Exception as e:
    print(f"[FAIL] Error importing MongoDB module: {e}")
    mongo_ok = False
    print()

# Test 3: Web Search Tool (Tavily)
print("[Test 3] Testing Web Search Tool (Tavily)...")
print("-" * 60)
try:
    from backend.core.tools.web_search import web_searchER

    print("   Query: 'current home loan interest rate India'")
    result = web_searchER.search("current home loan interest rate India", max_results=2)

    if result and "Error" not in result:
        print("[OK] Web search working!")
        # Show first 200 chars of result
        preview = result[:200] + "..." if len(result) > 200 else result
        print(f"   Result preview: {preview}")
        web_search_ok = True
    else:
        print(f"[FAIL] Web search failed: {result}")
        web_search_ok = False
    print()
except Exception as e:
    print(f"[FAIL] Web search error: {str(e)}")
    web_search_ok = False
    print()

# Test 4: Knowledge Base (RAG)
print("[Test 4] Testing Knowledge Base (RAG System)...")
print("-" * 60)
try:
    from backend.core.rag.knowledge_base import kb

    print("   Attempting to query knowledge base...")
    result = kb.query("home loan interest rates", k=3)

    if "Error" in result:
        print(f"[WARN] Knowledge base query failed: {result}")
        print("   This is expected if:")
        print("   1. You're using local MongoDB (vector search not supported)")
        print("   2. You haven't uploaded any documents yet")
        print("   3. MongoDB Atlas vector index not created")
        kb_ok = False
    elif "No relevant information" in result:
        print("[WARN] Knowledge base is empty (no documents uploaded)")
        print("   Status: Connection OK, but no data")
        kb_ok = True  # Connection works, just no data
    else:
        print("[OK] Knowledge base working!")
        preview = result[:200] + "..." if len(result) > 200 else result
        print(f"   Result preview: {preview}")
        kb_ok = True
    print()
except Exception as e:
    print(f"[FAIL] Knowledge base error: {str(e)}")
    print(f"   Full error: {type(e).__name__}: {e}")
    kb_ok = False
    print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
results = [
    ("Environment Variables", env_status),
    ("MongoDB Connection", mongo_ok),
    ("Web Search (Tavily)", web_search_ok),
    ("Knowledge Base (RAG)", kb_ok),
]

for name, status in results:
    icon = "[PASS]" if status else "[FAIL]"
    print(f"{icon} {name}")

print()
total = sum([1 for _, status in results if status])
print(f"Total: {total}/{len(results)} tests passed")
print()

if total == len(results):
    print("SUCCESS: All systems operational! Your Voice AI is ready to go!")
elif total >= 3:
    print("WARNING: Most systems working. Check failed components above.")
else:
    print("ERROR: Multiple failures detected. Review error messages above.")

print("=" * 60)
