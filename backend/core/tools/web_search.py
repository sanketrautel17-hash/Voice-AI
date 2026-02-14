import os
from tavily import TavilyClient
from commons.logger import logger

log = logger(__name__)


# Synchronous search wrapper using Tavily
class WebSearch:
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            log.warning("TAVILY_API_KEY not found in .env. Web search will fail.")
        else:
            self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, max_results: int = 3) -> str:
        """
        Perform a web search using Tavily API.
        Returns a formatted string of results.
        """
        try:
            if not self.api_key:
                return "Error: TAVILY_API_KEY not configured."

            log.info(f"Searching web with Tavily for: {query}")

            # search_depth="advanced" gives better results for AI agents
            response = self.client.search(
                query, search_depth="advanced", max_results=max_results
            )
            results = response.get("results", [])

            if not results:
                return "No relevant information found."

            formatted_results = []
            for result in results:
                title = result.get("title", "No Title")
                content = result.get("content", "")
                link = result.get("url", "")
                formatted_results.append(
                    f"Title: {title}\nSummary: {content}\nSource: {link}"
                )

            return "\n\n".join(formatted_results)
        except Exception as e:
            log.error(f"Web search failed: {e}")
            return f"Error performing web search: {str(e)}"


web_searchER = WebSearch()
