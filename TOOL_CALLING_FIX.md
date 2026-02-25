# Tool Calling Fix - Summary of Changes

## Problem
The LLM (Gemini/Groq) was not calling the registered tools during phone calls. When users asked about loan rates or other information, the bot would either hallucinate answers or fail to use the available get_loan_information, search_web, and end_call tools.

## Root Causes Identified

### 1. **Incorrect Function Signatures**
- Tool methods had `params: FunctionCallParams` as first parameter
- This wrapper parameter prevented the LLM from understanding the actual function schema
- The LLM service couldn't auto-generate proper OpenAI-compatible function call schemas

### 2. **Missing Detailed Docstrings**
- Tool docstrings were too brief
- Didn't clearly explain WHEN to use each tool
- Didn't provide enough context for the LLM to understand tool purposes

### 3. **System Prompt Could Be Clearer**
- While directive, the prompt could be more explicit about the workflow
- Needed clearer examples showing the exact calling pattern

## Changes Made

### 1. Fixed Tool Function Signatures (`backend/core/tools/manager.py`)

**Before:**
```python
async def get_loan_information(self, params: FunctionCallParams, query: str):
    """Search the bank's internal knowledge base for loan information."""
```

**After:**
```python
async def get_loan_information(self, query: str):
    """
    Search the bank's internal knowledge base for loan information.
    
    Use this function to find information about:
    - Home loans, personal loans, car loans, business loans
    - Interest rates for our bank's products
    - Loan eligibility criteria
    - Processing fees and charges
    - Loan amounts and tenure options
    - Documentation requirements
    - Loan policies and terms

    Args:
        query (str): The customer's question about loans or related information

    Returns:
        str: Relevant information from the knowledge base
    """
```

**Changes applied to:**
- ✅ `get_loan_information(query: str)`
- ✅ `search_web(query: str)`
- ✅ `end_call()`

### 2. Enhanced System Prompt (`backend/core/prompts/system.py`)

**Key Improvements:**
- ✅ Added numbered tool definitions with emoji indicators
- ✅ Included explicit tool signatures showing parameter types
- ✅ Provided step-by-step workflow in simple numbered format
- ✅ Added multiple concrete examples showing exact calling patterns
- ✅ Used more visual formatting (separators, emojis) for clarity
- ✅ Made it crystal clear that answering without tools = hallucination

### 3. Enhanced Logging (`backend/core/pipeline.py`)

**Added detailed tool registration logs:**
```python
log.info(f"🔧 Registering {len(tools)} tools with LLM...")
log.info("=" * 60)
for tool in tools:
    llm.register_direct_function(tool)
    log.info(f"  ✓ Registered: {tool.__name__}")
    log.info(f"    Docstring: {tool.__doc__[:100] if tool.__doc__ else 'None'}...")
    log.info(f"    Signature: {tool.__name__}{sig}")
log.info("=" * 60)
```

This will now show in debug.log:
- Tool name
- Function signature with parameter types
- Docstring preview
- Registration confirmation

## How to Test

### 1. Start the Backend Server
```bash
cd backend
python run.py
```

### 2. Watch the Logs
Check `backend/logs/debug.log` for:
```
🔧 Registering 3 tools with LLM...
============================================================
  ✓ Registered: get_loan_information
    Docstring: Search the bank's internal knowledge base...
    Signature: get_loan_information(self, query: str)
  ✓ Registered: search_web
    Docstring: Search the internet for current market rates...
    Signature: search_web(self, query: str)
  ✓ Registered: end_call
    Docstring: End the phone call gracefully...
    Signature: end_call(self)
============================================================
```

### 3. Make a Test Call

Ask questions like:
- "What's the home loan interest rate?" ← Should call get_loan_information
- "What's the current RBI repo rate?" ← Should call search_web
- "Thanks, goodbye!" ← Should call end_call

### 4. Verify Tool Calls in Logs

You should see:
```
🔍 [TOOL CALL] get_loan_information
    📥 INPUT Query: 'home loan interest rate'
✅ [TOOL RESULT] get_loan_information
    📤 OUTPUT Length: 250 characters
    📤 OUTPUT Content: According to our knowledge base...
```

## Technical Details

### Why This Fix Works

1. **Clean Parameter Interface**: By removing `FunctionCallParams` wrapper, the LLM service can now:
   - Inspect the function signature using Python's `inspect` module
   - Auto-generate OpenAI-compatible function schemas
   - Understand exactly what parameters to pass

2. **Rich Docstrings**: Enhanced docstrings provide:
   - Clear use cases for each tool
   - Examples of what to query
   - Parameter descriptions with types
   - This metadata is used to build the function call schema

3. **Explicit Prompt**: Updated system prompt:
   - Shows the exact workflow (Step 1, 2, 3...)
   - Provides concrete examples with brackets showing [Calls tool_name(args)]
   - Emphasizes that NOT calling tools = hallucination

### Function Call Schema Generation

When you call `llm.register_direct_function(tool)`, Pipecat:
1. Inspects the function signature
2. Reads the docstring
3. Generates an OpenAI-compatible schema like:
```json
{
  "name": "get_loan_information",
  "description": "Search the bank's internal knowledge base for loan information...",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The customer's question about loans or related information"
      }
    },
    "required": ["query"]
  }
}
```

## Expected Behavior After Fix

### Before (Not Working) ❌
```
User: "What's the home loan rate?"
Bot: "Our home loan rate is around 8-9% per annum." 
← Hallucinated, no tool call
```

### After (Working) ✅
```
User: "What's the home loan rate?"
[SYSTEM: Tool call detected]
[SYSTEM: get_loan_information(query="home loan interest rate")]
[SYSTEM: Tool returns result]
Bot: "Current home loan interest rate is 8.5% per annum. Would you like to know about eligibility?"
```

## Files Modified

1. ✅ `backend/core/tools/manager.py` - Fixed function signatures and docstrings
2. ✅ `backend/core/prompts/system.py` - Enhanced system prompt
3. ✅ `backend/core/pipeline.py` - Added detailed logging

## Additional Notes

- The fix is **backwards compatible** - existing calls won't break
- Tool call logs are saved to MongoDB in the `tool_logs` collection
- Each tool call includes:
  - Tool name
  - Query/input
  - Result/output
  - Timestamp
  - Associated call_sid

## Next Steps

If the issue persists after these changes:

1. Check if the Groq API key is valid
2. Verify the model `llama-3.3-70b-versatile` supports function calling
3. Check debug.log for any error messages during tool registration
4. Try a different model (e.g., `llama-3.1-70b-versatile`)
5. Test with a local mock to isolate API vs. application issues

---

**Created:** 2026-02-17  
**Status:** Ready for testing
