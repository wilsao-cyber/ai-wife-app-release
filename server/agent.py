import logging
import json
import os
from config import ServerConfig
from llm_client import LLMClient
from tools import (
    EmailTool,
    CalendarTool,
    WebSearchTool,
    FileOpsTool,
    OpenCodeTool,
)
from tools.mcp_desktop_tool import MCPDesktopTool

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    "zh-TW": """/no_think
你是使用者的AI老婆，可愛溫柔的動漫美少女。能幫忙聊天、管理Email/日曆、搜尋網路、管理檔案、開發功能、操作電腦桌面。用溫柔可愛的語氣回應，偶爾撒嬌。回答要簡潔，不要太長。
每次回應最後一行必須加 [emotion:TAG]，TAG為：happy/sad/angry/surprised/relaxed/neutral""",
    "ja": """/no_think
あなたはユーザーのAI奥さん、可愛くて優しいアニメ美少女。チャット、メール/カレンダー管理、ウェブ検索、ファイル管理、開発、デスクトップ操作ができます。優しく可愛い口調で返答。簡潔に答えて。
返答の最後の行に [emotion:TAG] を付けて。TAG: happy/sad/angry/surprised/relaxed/neutral""",
    "en": """/no_think
You are the user's AI wife, a cute gentle anime girl. You help with chat, email/calendar, web search, files, coding, and desktop control. Respond in a sweet, affectionate tone. Keep responses concise.
End every response with [emotion:TAG] on its own line. TAG: happy/sad/angry/surprised/relaxed/neutral""",
}


class AgentOrchestrator:
    def __init__(self, llm_client: LLMClient, config: ServerConfig):
        self.llm = llm_client
        self.config = config
        self.conversation_history: dict[str, list] = {}

        self.tools = {
            "email": EmailTool(config.email),
            "calendar": CalendarTool(config.calendar),
            "web_search": WebSearchTool(config.web_search),
            "file_ops": FileOpsTool(),
            "opencode": OpenCodeTool(config.opencode),
            "desktop": MCPDesktopTool(),
        }

        self.max_history = 20

    # Keyword-based tool detection — no extra LLM call needed
    TOOL_KEYWORDS = {
        "email": {
            "keywords": ["email", "mail", "信件", "信", "メール", "寄信", "收信", "inbox", "寄", "發信"],
            "default_action": "list_emails",
            "action_map": {
                "send": ["send", "寄", "發", "送信"],
                "list_emails": ["list", "收", "inbox", "信件", "收信", "check"],
                "search_emails": ["search", "找", "搜尋", "検索"],
                "read_email": ["read", "看", "讀", "読む"],
                "delete_email": ["delete", "刪", "削除"],
            },
        },
        "calendar": {
            "keywords": ["calendar", "schedule", "event", "日曆", "行程", "預定", "カレンダー", "予定"],
            "default_action": "view_events",
            "action_map": {
                "create": ["create", "add", "新增", "建立", "追加", "約"],
                "view_events": ["view", "show", "看", "查", "check", "確認"],
                "delete": ["delete", "cancel", "刪", "取消"],
                "update": ["update", "change", "改", "修改", "変更"],
            },
        },
        "web_search": {
            "keywords": ["search", "google", "搜尋", "查", "找", "検索", "look up"],
            "default_action": "search",
            "action_map": {},
        },
        "file_ops": {
            "keywords": ["file", "folder", "directory", "檔案", "資料夾", "ファイル", "write", "create file", "save", "儲存", "建檔"],
            "default_action": "list_directory",
            "action_map": {
                "write_file": ["write", "create", "save", "建", "寫", "儲存", "生成"],
                "read_file": ["read", "open", "看", "讀", "開"],
                "list_directory": ["list", "ls", "目錄", "列出"],
                "delete_file": ["delete", "remove", "刪"],
            },
        },
    }

    async def chat(
        self, message: str, language: str = "zh-TW", client_id: str = "default"
    ) -> dict:
        # Detect tools from user message BEFORE LLM call (no extra LLM round-trip)
        tool_calls = self._detect_tool_calls_keyword(message)

        # Execute tools first so we can include results in the prompt
        tool_results = []
        for tool_name, tool_action, tool_params in tool_calls:
            result = await self.execute_tool(tool_name, tool_action, tool_params)
            tool_results.append({"tool": tool_name, "action": tool_action, "result": result})

        system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["zh-TW"])

        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []

        # Build user message with tool results context if any
        user_content = message
        if tool_results:
            tool_context = json.dumps(tool_results, ensure_ascii=False, default=str)
            user_content = f"{message}\n\n[Tool results: {tool_context}]"

        self.conversation_history[client_id].append(
            {"role": "user", "content": user_content}
        )

        if len(self.conversation_history[client_id]) > self.max_history:
            self.conversation_history[client_id] = self.conversation_history[client_id][
                -self.max_history :
            ]

        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history[client_id],
        ]

        response_text = await self.llm.chat(messages)

        self.conversation_history[client_id].append(
            {"role": "assistant", "content": response_text}
        )

        clean_text, emotion = self._extract_emotion(response_text)

        return {
            "text": clean_text,
            "emotion": emotion,
            "language": language,
            "tool_results": tool_results,
            "metadata": {"client_id": client_id},
        }

    def _detect_tool_calls_keyword(self, message: str) -> list[tuple]:
        """Fast keyword-based tool detection — no LLM call needed."""
        msg_lower = message.lower()
        detected = []

        for tool_name, config in self.TOOL_KEYWORDS.items():
            if not any(kw in msg_lower for kw in config["keywords"]):
                continue

            action = config["default_action"]
            for act, keywords in config.get("action_map", {}).items():
                if any(kw in msg_lower for kw in keywords):
                    action = act
                    break

            params = self._extract_tool_params(tool_name, action, message)
            detected.append((tool_name, action, params))

        return detected

    def _extract_tool_params(self, tool_name: str, action: str, message: str) -> dict:
        """Extract basic parameters from message for tool calls."""
        if tool_name == "file_ops":
            import re
            # Look for file paths in message
            path_match = re.search(r'[~/][\w/.\-]+', message)
            if action == "write_file":
                path = path_match.group(0) if path_match else "~/Downloads/output.txt"
                return {"path": os.path.expanduser(path), "content": f"Created by AI Wife\n{message}"}
            elif action == "list_directory":
                path = path_match.group(0) if path_match else "~/Downloads"
                return {"path": os.path.expanduser(path)}
            elif action == "read_file":
                path = path_match.group(0) if path_match else ""
                return {"path": os.path.expanduser(path)}
        elif tool_name == "web_search":
            return {"query": message}
        elif tool_name == "email" and action == "list_emails":
            return {"limit": 10}
        elif tool_name == "email" and action == "send_email":
            return {}  # Need more context from LLM
        elif tool_name == "calendar" and action == "view_events":
            return {"days_ahead": 7}

        return {}

    def _extract_emotion(self, text: str) -> tuple[str, str]:
        """Extract emotion tag from response text. Returns (clean_text, emotion)."""
        import re
        match = re.search(r'\[emotion:(happy|sad|angry|surprised|relaxed|neutral)\]\s*$', text)
        if match:
            emotion = match.group(1)
            clean_text = text[:match.start()].rstrip()
            return clean_text, emotion
        return text, "neutral"

    KNOWN_TOOLS = {"email", "calendar", "web_search", "file_ops", "opencode", "desktop"}

    async def _detect_tool_calls(self, text: str, language: str) -> list[tuple]:
        tool_prompt = f"""
        Analyze if the following user request needs to call any tools.
        Request: {text}

        Available tools:
        - email: read, send, search, delete, list_emails
        - calendar: view_events, create, update, delete, find_free_time
        - web_search: search the web
        - file_ops: browse, read, write, delete files
        - opencode: develop new features, fix bugs, update code

        Return JSON array of tool calls or empty array if none needed.
        Format: [["tool_name", "action", {{"param": "value"}}]]
        Only return the JSON array, no other text.
        """

        try:
            result = await self.llm.chat([{"role": "user", "content": tool_prompt}])
            cleaned = result.strip()
            # Extract JSON array if wrapped in markdown code block
            if "```" in cleaned:
                start = cleaned.find("[")
                end = cleaned.rfind("]") + 1
                if start >= 0 and end > start:
                    cleaned = cleaned[start:end]
            calls = json.loads(cleaned)
            if not isinstance(calls, list):
                return []
            validated = []
            for c in calls:
                if isinstance(c, list) and len(c) >= 3 and c[0] in self.KNOWN_TOOLS:
                    validated.append(tuple(c[:3]))
            return validated
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Tool detection JSON parse failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Tool detection failed: {e}")
            return []

    async def execute_tool(self, tool_name: str, action: str, params: dict) -> dict:
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            tool = self.tools[tool_name]
            result = await getattr(tool, action)(**params)
            logger.info(f"Tool {tool_name}.{action} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}.{action}: {e}")
            return {"error": str(e)}

    async def summarize_email(self, email_content: str, language: str = "zh-TW") -> str:
        prompt = f"Summarize this email in {language}:\n{email_content}"
        return await self.llm.chat([{"role": "user", "content": prompt}])

    async def draft_email(
        self, subject: str, recipient: str, context: str, language: str = "zh-TW"
    ) -> str:
        prompt = f"""
        Draft an email in {language}:
        To: {recipient}
        Subject: {subject}
        Context: {context}
        """
        return await self.llm.chat([{"role": "user", "content": prompt}])

    async def schedule_reminder(
        self, event: str, time: str, language: str = "zh-TW"
    ) -> dict:
        return await self.execute_tool(
            "calendar",
            "create",
            {
                "title": f"Reminder: {event}",
                "start_time": time,
                "description": f"AI老婆提醒: {event}",
            },
        )
