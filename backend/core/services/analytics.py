import os
import json
import asyncio
from groq import AsyncGroq
from core.prompts.system import ANALYSIS_PROMPT_TEMPLATE
from commons.logger import logger

log = logger(__name__)


async def analyze_call_transcript(transcript_data: list):
    """
    Analyzes the call transcript using Groq LLM to extract insights.
    """
    try:
        # Format the transcript for analysis
        transcript_str = str(transcript_data)[:10000]  # Truncate if too long

        # Construct the prompt
        analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(transcript=transcript_str)

        # Initialize AsyncGroq client
        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": analysis_prompt}],
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()

        # Clean up response text to ensure it's valid JSON
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]

        return json.loads(text)
    except Exception as e:
        log.error(f"Failed to analyze call: {e}")
        return {"error": str(e), "is_interested": False}
