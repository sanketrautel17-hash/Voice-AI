import asyncio
import sys
from datetime import datetime
from pipecat.frames.frames import TextFrame, EndFrame
from core.db.database import get_database
from core.rag.knowledge_base import kb
from core.tools.web_search import web_searchER
from commons.logger import logger

log = logger(__name__)


class ToolManager:
    def __init__(self, task, call_sid):
        self.task = task
        self.call_sid = call_sid
        self.db = get_database()

    async def log_tool_usage(self, tool_name: str, query: str, result: str):
        try:
            log.info(f"EXECUTING TOOL: {tool_name} | Query: {query}")
            if self.db is not None:
                log_entry = {
                    "call_sid": self.call_sid,
                    "tool": tool_name,
                    "query": query,
                    "result": str(result),
                    "timestamp": datetime.now(),
                }
                await self.db["tool_logs"].insert_one(log_entry)
                log.info(f"TOOL RESULT LOGGED: {str(result)[:100]}...")
            else:
                log.warning("Database instance not available for logging tool usage")
        except Exception as e:
            log.error(f"Failed to log tool usage: {e}")

    async def get_loan_information(self, params, query: str):
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
        try:
            log.info(f"🔍 [TOOL CALL] get_loan_information")
            log.info(f"    📥 INPUT Query: '{query}'")

            # Call the knowledge base
            result = await asyncio.to_thread(kb.query, query)

            # Ensure we have a valid result
            if result is None or str(result).strip() == "":
                result = "I couldn't find specific information about that in our knowledge base. Let me connect you with a loan officer who can provide accurate details."

            # Convert to string
            result_str = str(result).strip()

            log.info(f"✅ [TOOL RESULT] get_loan_information")
            log.info(f"    📤 OUTPUT Length: {len(result_str)} characters")
            log.info(f"    📤 OUTPUT Content: {result_str[:300]}...")

            # Log to database
            await self.log_tool_usage("get_loan_information", query, result_str)

            return result_str

        except Exception as e:
            error_msg = f"I'm experiencing technical difficulties accessing our loan database. Please hold while I transfer you to a loan officer, or you can try again in a moment."
            log.error(f"❌ [TOOL ERROR] get_loan_information: {str(e)}")
            await self.log_tool_usage("get_loan_information", query, f"ERROR: {str(e)}")
            return error_msg

    async def search_web(self, params, query: str):
        """
        Search the internet for current market rates and external information.

        Use this function to find:
        - Current market interest rates
        - RBI policy rates and guidelines
        - Competitor loan products
        - General banking information
        - Industry trends and news

        Args:
            query (str): The search query for web information

        Returns:
            str: Information from web search results
        """
        try:
            log.info(f"🌐 [TOOL CALL] search_web")
            log.info(f"    📥 INPUT Query: '{query}'")

            # Call web search
            result = await asyncio.to_thread(web_searchER.search, query)

            # Ensure we have a valid result
            if result is None or str(result).strip() == "":
                result = "I couldn't find current information about that online. Would you like to know about our internal loan products instead?"

            # Convert to string
            result_str = str(result).strip()

            log.info(f"✅ [TOOL RESULT] search_web")
            log.info(f"    📤 OUTPUT Length: {len(result_str)} characters")
            log.info(f"    📤 OUTPUT Content: {result_str[:300]}...")

            # Log to database
            await self.log_tool_usage("search_web", query, result_str)

            return result_str

        except Exception as e:
            error_msg = f"I'm unable to search for that information right now. Would you like to know about our bank's loan products instead?"
            log.error(f"❌ [TOOL ERROR] search_web: {str(e)}")
            await self.log_tool_usage("search_web", query, f"ERROR: {str(e)}")
            return error_msg

    async def end_call(self, params):
        """
        End the phone call gracefully after saying goodbye.

        Use this function when:
        - The customer says goodbye, thanks, or wants to end the call
        - The conversation has naturally concluded
        - The customer explicitly asks to disconnect

        Returns:
            str: Confirmation that call termination was initiated
        """
        try:
            log.info("🛑 [TOOL CALL] end_call")

            await self.log_tool_usage("end_call", "N/A", "Call termination requested")

            if self.task:
                await self.task.queue_frames(
                    [
                        TextFrame(
                            text="Thank you for calling. Have a wonderful day! Goodbye."
                        ),
                    ]
                )

                await asyncio.sleep(1.5)
                await self.task.queue_frames([EndFrame()])
                log.info("✅ [TOOL RESULT] end_call - Call terminated")
            else:
                log.error("❌ [TOOL ERROR] end_call: Task not initialized")

            return "Call ended successfully."

        except Exception as e:
            log.error(f"❌ [TOOL ERROR] end_call: {e}")
            return "Error ending call."
