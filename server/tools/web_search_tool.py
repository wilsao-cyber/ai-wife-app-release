import logging
import httpx
from typing import Optional
from config import WebSearchConfig

logger = logging.getLogger(__name__)


class WebSearchTool:
    def __init__(self, config: WebSearchConfig):
        self.config = config
        self.provider = config.provider
        self.base_url = config.base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        num_results: int = 10,
        language: str = "zh-TW",
    ) -> dict:
        if self.provider == "searxng":
            return await self._search_searxng(query, num_results, language)
        elif self.provider == "tavily":
            return await self._search_tavily(query, num_results, language)
        else:
            return {"error": f"Unsupported search provider: {self.provider}"}

    async def _search_searxng(
        self, query: str, num_results: int, language: str
    ) -> dict:
        try:
            lang_map = {"zh-TW": "zh-TW", "ja": "ja", "en": "en"}
            response = await self.client.get(
                f"{self.base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                    "language": lang_map.get(language, "en"),
                    "engines": "google,bing,duckduckgo",
                    "results": num_results,
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", [])[:num_results]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),
                    }
                )

            return {"results": results, "total": len(results), "query": query}
        except Exception as e:
            logger.error(f"SearXNG search failed: {e}")
            return {"error": str(e), "query": query}

    async def _search_tavily(self, query: str, num_results: int, language: str) -> dict:
        try:
            import os

            api_key = os.getenv("TAVILY_API_KEY", "")
            response = await self.client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": num_results,
                    "search_depth": "advanced",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", [])[:num_results]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),
                        "score": item.get("score", 0),
                    }
                )

            return {"results": results, "total": len(results), "query": query}
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return {"error": str(e), "query": query}

    async def fetch_page_content(self, url: str) -> dict:
        try:
            response = await self.client.get(url)
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

    async def close(self):
        await self.client.aclose()
