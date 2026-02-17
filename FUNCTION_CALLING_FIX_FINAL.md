# Function Calling Fix - Updated Strategy

## What We've Learned

### ❌ Models That DON'T Work:
1. **`llama-3.3-70b-versatile`** - Your original model
   - Tools registered successfully
   - But LLM completely ignored them
   - Hallucinated rates instead

2. **`llama3-groq-70b-8192-tool-use-preview`** - Deprecated!
   - Error: "model has been decommissioned"
   - Groq shut it down

### ✅ Current Recommended Model:
**`openai/gpt-oss-120b`**

According to Groq's 2026 documentation:
- OpenAI's flagship open-weight model on Groq
- Built-in browser search and code execution
- Specifically listed for "Function Calling / Tool Use"
- Has automatic prompt caching (50% cost savings)
- Better tool-use capabilities than previous models

## Changes Applied

**File**: `backend/core/pipeline.py`

```python
# Changed from:
model="llama-3.3-70b-versatile"

# To:
model="openai/gpt-oss-120b"
```

## Alternative Models to Try (If Needed)

If `gpt-oss-120b` doesn't work, try these in order:

1. **`openai/gpt-oss-20b`** - Smaller, faster version
   - Also recommended for function calling
   - Lower latency

2. **`qwen/qwen-2.5-coder-32b-instruct`** - Strong coding/reasoning
   - Listed for function calling support
   - Good at structured tasks

3. **`meta-llama/llama-3.1-70b-versatile`** - Previous stable version
   - Well-documented
   - Proven function calling

4. **OpenAI GPT-4** (if you have API access)
   - Switch from GroqLLMService to OpenAILLMService
   - Gold standard for function calling
   - Most reliable but slower/more expensive

## Testing Steps

1. **Restart backend**:
   ```bash
   cd backend
   python run.py
   ```

2. **Make test call** and ask clearly:
   - "What is the home loan interest rate?"
   - "Tell me about your loan products"

3. **Check logs** for:
   ```
   🔍 [TOOL CALL] get_loan_information
       📥 INPUT Query: 'home loan interest rate'
   ✅ [TOOL RESULT] get_loan_information
       📤 OUTPUT: [actual data]
   ```

4. **Success indicators**:
   - ✅ Tool call logs appear
   - ✅ Bot uses actual data from knowledge base/web search
   - ✅ No hallucinated rates

5. **Failure indicators**:
   - ❌ No tool call logs
   - ❌ Bot makes up answers
   - ❌ Gives specific rates without calling tools

## Debugging Strategy

If this STILL doesn't work:

### Check 1: Is knowledge base empty?
```python
# Run this test
python test_tools_detailed.py
```
Look for the RAG test - if it says "no documents", that's fine for now. Use search_web instead.

### Check 2: Try forcing tool use
Edit `backend/core/pipeline.py`:
```python
from pipecat.services.groq import GroqLLMServiceParams

llm = GroqLLMService(
    api_key=os.getenv("GROQ_API_KEY"),
    model="openai/gpt-oss-120b",
    params=GroqLLMServiceParams(
        extra={"tool_choice": "auto"}
    )
)
```

### Check 3: Simplify system prompt even more
Replace with ultra-minimal version:
```python
SYSTEM_PROMPT = """You are FinBot.

RULE: For ANY question about rates, loans, eligibility, fees → 
MUST call get_loan_information(query) or search_web(query) FIRST.

Never answer from memory. Always use tools."""
```

### Check 4: Switch to OpenAI (most reliable)
If you have OpenAI API access:
```python
from pipecat.services.openai import OpenAILLMService

llm = OpenAILLMService(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",  # or "gpt-4"
)
```

## Expected Behavior After Fix

**User**: "What's the home loan rate?"

**Log Output**:
```
[INFO] - [🔍 [TOOL CALL] get_loan_information]
[INFO] - [    📥 INPUT Query: 'home loan interest rate']
[INFO] - [✅ [TOOL RESULT] get_loan_information]  
[INFO] - [    📤 OUTPUT: According to our knowledge base, rates range from X% to Y%...]
```

**Bot Response**: "[Based on actual data from tool]"

---

**Current Status**: Testing `openai/gpt-oss-120b` model  
**Next**: Restart backend and test with a call
