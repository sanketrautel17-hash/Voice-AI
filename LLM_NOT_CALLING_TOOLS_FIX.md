# LLM NOT CALLING TOOLS - Analysis & Solution

## CONFIRMED ISSUE from Debug Logs

Looking at your `backend/logs/debug.log` (lines 54-134), I can confirm:

### ✅ What's Working:
1. Tools are registered successfully with the LLM
2. Function signatures are correct (`params` as first parameter)
3. Docstrings are present and detailed
4. System prompt is loaded

### ❌ What's NOT Working:
**The LLM is completely ignoring the tools!**

Evidence from logs:
- Line 63-64: User asks: "what is the rate of interest for the whole loan from the bank?"
- Line 65, 66, 69, 71: User repeats: "so what is the rate of interest?" 
- Lines 112-116: User asks: "what is the rate of interest for home loan from the bank of maharashtra?"

**EXPECTED**: Should see logs like:
```
🔍 [TOOL CALL] get_loan_information
     📥 INPUT Query: 'home loan interest rate'
✅ [TOOL RESULT] get_loan_information
```

**ACTUAL**: NO tool call logs appear at all!

Instead, the bot hallucinated a rate (8.4%), and the user corrected it (line 125).

## ROOT CAUSE

The issue is likely one of these:

### 1. **Model May Not Support Function Calling Properly**
`llama-3.3-70b-versatile` might have limited function calling support compared to other models.

### 2. **System Prompt Is Too Complex**
The LLM may be confused by the long examples and narrative style.

### 3. **Tool Call Format Not Recognized**
Groq's implementation may expect different schema formatting.

## SOLUTIONS TO TRY

### Solution 1: Try a Different Model (RECOMMENDED)

The `llama-3.1-70b-versatile` model has better documented function calling support.

**Change in `backend/core/pipeline.py` line 51:**
```python
# FROM:
model="llama-3.3-70b-versatile",

# TO:
model="llama-3.1-70b-versatile",
```

Or try the specialized tool-use model:
```python
model="llama3-groq-70b-8192-tool-use-preview",
```

### Solution 2: Simplify the System Prompt

The current prompt may be too verbose. Try this ultra-simple version:

```python
SYSTEM_PROMPT = """You are FinBot, a bank loan assistant.

CRITICAL RULE: You MUST call tools for ANY question about:
- Interest rates
- Loan policies
- Eligibility
- Fees
- Documentation

TOOLS:
1. get_loan_information(query) - For OUR bank's products
2. search_web(query) - For market/RBI rates  
3. end_call() - When user says goodbye

WORKFLOW GUARANTEE:
Rate question → Call get_loan_information() or search_web() → Answer from tool result
NO exceptions.

If you answer WITHOUT calling a tool first = WRONG.
"""
```

### Solution 3: Enable Tool Choice (Force Tool Use)

Some LLMs need explicit forcing. Check if Groq supports `tool_choice` parameter:

In `backend/core/pipeline.py`, try adding to GroqLLMService:
```python
llm = GroqLLMService(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-70b-versatile",
    params=GroqLLMServiceParams(
        # Try forcing tool use
        extra={"tool_choice": "auto"}  # or "required"
    )
)
```

### Solution 4: Check Function Schema Generation

Add debug logging to see what schema is being sent to Groq:

In `backend/core/pipeline.py`, after tool registration:
```python
# After line 132 (after registering tools)
if hasattr(llm, '_tools') or hasattr(llm, 'tools'):
    tools_attr = getattr(llm, '_tools', None) or getattr(llm, 'tools', None)
    log.info(f"📋 Registered tool schemas:")
    for tool_name, tool_schema in (tools_attr or {}).items():
        log.info(f"  Tool: {tool_name}")
        log.info(f"  Schema: {tool_schema}")
```

## IMMEDIATE ACTION PLAN

1. **First, try changing the model** (easiest fix):
   - Edit `backend/core/pipeline.py` line 51
   - Change to `llama3-groq-70b-8192-tool-use-preview`
   
2. **Restart backend**:
   ```bash
   cd backend
   python run.py
   ```

3. **Make a test call** and ask: "What's the home loan rate?"

4. **Check logs** for tool call indicators:
   ```
   🔍 [TOOL CALL] get_loan_information
   ```

5. **If still not working**, try Solution 2 (simplify prompt)

## How To Verify

You'll know it's fixed when you see in `debug.log`:
```
[INFO] - [🔍 [TOOL CALL] get_loan_information]
[INFO] - [    📥 INPUT Query: 'home loan interest rate']
[INFO] - [✅ [TOOL RESULT] get_loan_information]
[INFO] - [    📤 OUTPUT: ...]
```

## Additional Debugging

If none of the above work, we may need to:
1. Check if Pipecat version supports Groq function calling
2. Test with OpenAI's model instead (gpt-4 known to work well with function calling)
3. Create a minimal reproduction case to isolate the issue

---

**Status**: Tools are registered correctly, but LLM is not calling them.  
**Next Step**: Try model  change first (Solution 1).
