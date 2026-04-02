import logging
from typing import Optional
from config import WebSearchConfig

logger = logging.getLogger(__name__)


class WebSearchTool:
    def __init__(self, config: WebSearchConfig):
        self.config = config
        self.provider = (
            "duckduckgo"  # Always use DuckDuckGo, no external service needed
        )

    async def search(
        self,
        query: str,
        num_results: int = 10,
        language: str = "zh-TW",
    ) -> dict:
        return await self._search_duckduckgo(query, num_results, language)

    async def _search_duckduckgo(
        self, query: str, num_results: int, language: str
    ) -> dict:
        try:
            from duckduckgo_search import DDGS

            region_map = {"zh-TW": "tw-tw", "ja": "jp-jp", "en": "us-en"}
            region = region_map.get(language, "us-en")

            with DDGS() as ddgs:
                raw = list(
                    ddgs.text(keywords=query, max_results=num_results, region=region)
                )

            results = []
            for item in raw:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                    }
                )

            return {"results": results, "total": len(results), "query": query}
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return {"error": str(e), "query": query}

    async def fetch_page_content(self, url: str) -> dict:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.text, "html.parser")
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator="\n", strip=True)
                return {"url": url, "content": text[:5000]}
        except Exception as e:
            logger.error(f"Fetch page failed: {e}")
            return {"error": str(e), "url": url}
