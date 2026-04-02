from skills.base_skill import BaseSkill
from tools.web_search_tool import WebSearchTool
from config import config


class SearchSkill(BaseSkill):
    def __init__(self):
        self._tool = WebSearchTool(config.web_search)

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "在網路上搜尋最新資訊 (Search the web for latest information). 搜尋關鍵字不要加日期，搜尋引擎會自動排序最新結果。如果搜尋失敗會回傳 error 欄位，你必須誠實告知用戶搜尋失敗，不要假裝有結果。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜尋關鍵字（不要加日期），例如：TSMC stock price、台積電股價",
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "回傳的搜尋結果數量，預設 5，最少 5",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, **kwargs) -> dict:
        if tool_name == "web_search":
            return await self._tool.search(
                query=kwargs["query"],
                num_results=max(5, kwargs.get("num_results", 5)),
            )
        return {"error": f"Unknown search tool: {tool_name}"}
