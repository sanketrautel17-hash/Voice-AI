# Tool Calling Issues - Diagnosis & Fix

**Date:** 2026-02-14  
**Issues Reported:**
1. Bot not using tools to answer questions about loan rates
2. end_call() not working when user says goodbye

---

## 🔍 **Root Cause Analysis**

### Issue 1: Tools Not Being Called

**Symptoms:**
- User asks: "What is the current rate of interest for home loan from RBI bank?"
- Bot responds without calling `search_web()` or `get_loan_information()`
- No tool execution logs in debug.log

**Potential Causes:**

1. **LLM Not Receiving Tool Schemas** ✅ FIXED
   - We removed `extra={"tools": tool_schemas}` from LLM initialization
   - Now using only `register_direct_function()` which is correct
   
2. **System Prompt Not Clear Enough** ✅ FIXED
   - Updated prompt with explicit examples
   - Added visual separators and step-by-step instructions
   
3. **Groq Model Limitations** ⚠️ POSSIBLE
   - llama-3.3-70b-versatile might not be as good at tool calling
   - Consider: llama-3.1-70b-versatile or mixtral models

4. **Pipecat Version Issue** ⚠️ TO CHECK
   - Pipecat 0.0.102 might have bugs with Groq tool calling
   - Need to verify tool calls are actually being sent to API

---

## ✅ **Fixes Applied**

### Fix 1: Enhanced System Prompt

**Location:** `backend/core/pipeline.py` line 107-148

**Changes:**
- Added clear visual sections with separators
- Included concrete examples of WHEN to call each tool
- Emphasized "IMMEDIATELY" and "MUST" for critical actions
- Step-by-step workflow: Use tool → Share result → Ask if need more

**New Prompt Structure:**
```
⚠️ YOU MUST USE TOOLS
═══════════════════
🔧 TOOL USAGE (MANDATORY):
1️⃣ RATES/LOANS → get_loan_information()
2️⃣ RBI/MARKET → search_web()
3️⃣ BYE/THANKS → end_call()

📝 EXAMPLES:
[Concrete examples with exact function calls]

⚡ REMEMBER:
[Step-by-step reminders]
```

---

## 🧪 **How to Verify the Fix**

### Step 1: Restart the Server

```bash
cd backend
# Stop existing server
taskkill /F /PID $(netstat -ano | findstr :8000 | awk '{print $5}')

# Start fresh
.\venv\Scripts\python.exe run.py
```

### Step 2: Make a Test Call

Ask these specific questions:

1. **Test get_loan_information:**
   - "What's your home loan interest rate?"
   - Expected: Should call `get_loan_information(query="home loan interest rate")`

2. **Test search_web:**
   - "What's the current RBI home loan rate?"
   - Expected: Should call `search_web(query="current RBI home loan interest rate India 2026")`

3. **Test end_call:**
   - "Thanks, goodbye!"
   - Expected: Should call `end_call()` and disconnect

### Step 3: Monitor Logs

**Enable Pipecat logging:**

Create `backend/logging_config.py`:
```python
import logging

# Set Pipecat to DEBUG
logging.getLogger("pipecat").setLevel(logging.DEBUG)
```

Then in `backend/run.py`, add at the top:
```python
import logging_config
```

**Watch for these log patterns:**
- `"Calling function: get_loan_information"`
- `"Calling function: search_web"`
- `"Calling function: end_call"`
- `"tool_call"` or `"function_call"` in Pipecat logs

---

## 🔧 **Additional Troubleshooting**

### If Tools Still Don't Work:

#### Option 1: Try Different Groq Model

Change in `pipeline.py` line 100:
```python
# Current
model="llama-3.3-70b-versatile",

# Try this instead
model="llama-3.1-70b-versatile",  # Better tool calling support
```

#### Option 2: Add Function Calling Parameter

In `pipeline.py` line 98-101:
```python
llm = GroqLLMService(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    params=BaseOpenAILLMService.InputParams(
        extra={"tool_choice": "auto"}  # Force tool consideration
    ),
)
```

#### Option 3: Simplify System Prompt

If the prompt is too complex, the model might ignore instructions. Try:
```python
"content": """You are FinBot. You have 3 tools:
1. get_loan_information(query) - Use for ANY loan question
2. search_web(query) - Use for market/RBI rates
3. end_call() - Use when user says bye

ALWAYS use a tool before answering. When user says bye, call end_call()."""
```

---

## 📊 **Debugging Commands**

### Check if tools are registered:
```bash
python test_tool_calling.py
```

### Monitor server in real-time:
```powershell
Get-Content backend/logs/debug.log -Wait -Tail 50 | Select-String "tool|function|end_call|search_web|get_loan"
```

### Check Groq API directly:
```python
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You have tools. Use search_web for market rates."},
        {"role": "user", "content": "What's the RBI rate?"}
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
        }
    }],
    tool_choice="auto"
)

print(response.choices[0].message)
# Should show tool_calls if working
```

---

## 🎯 **Next Steps**

1. **Restart server** with new prompt
2. **Make test calls** with specific questions
3. **Monitor logs** for tool execution
4. **If still not working:**
   - Try llama-3.1-70b-versatile model
   - Simplify system prompt
   - Check Pipecat GitHub issues for similar problems

---

## 📝 **Expected Behavior After Fix**

### Scenario 1: RBI Rate Question
```
User: "What is the current rate of interest for home loan from RBI?"

Bot Process:
1. ✅ Recognizes "RBI" + "rate" keywords
2. ✅ Calls search_web(query="current RBI home loan interest rate India 2026")
3. ✅ Receives search results from Tavily
4. ✅ Summarizes findings to user
5. ✅ Asks "Is there anything else I can help with?"
```

### Scenario 2: End Call
```
User: "Thanks, goodbye!"

Bot Process:
1. ✅ Recognizes goodbye intent
2. ✅ Calls end_call()
3. ✅ Says "Thank you for your time. Have a great day! Goodbye."
4. ✅ Waits 1.5 seconds
5. ✅ Sends EndFrame to disconnect
6. ✅ Call terminates
```

---

**Status:** ✅ Fixes Applied  
**Testing Required:** Yes - make a test call  
**Estimated Impact:** Should resolve both issues
