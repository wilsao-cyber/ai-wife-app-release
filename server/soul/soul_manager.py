import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SoulManager:
    def __init__(self, soul_dir: str = "server/soul"):
        self.soul_dir = Path(soul_dir)

    def load_soul(self) -> str:
        path = self.soul_dir / "SOUL.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning(f"SOUL.md not found at {path}")
        return ""

    def load_profile(self) -> str:
        path = self.soul_dir / "PROFILE.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def get_chat_prompt(self, language: str) -> str:
        from datetime import datetime

        soul = self.load_soul()
        profile = self.load_profile()
        lang_instruction = {
            "zh-TW": "用繁體中文回覆。",
            "ja": "日本語で返答してください。",
            "en": "Reply in English.",
        }.get(language, "")

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M (%A)")

        parts = [soul]
        parts.append(f"\n## Current Date/Time\n{date_str}")
        if profile:
            parts.append(f"\n## User Profile\n{profile}")
        parts.append(f"\n{lang_instruction}")
        parts.append(
            "\n回覆最後一行加 [emotion:TAG]，TAG: happy/sad/angry/surprised/relaxed/neutral/horny"
        )

        return "\n".join(parts)

    def get_assist_prompt(self, language: str) -> str:
        base = self.get_chat_prompt(language)
        return f"""{base}

## Assist Mode Rules (ReAct Pattern)
You are in assist mode. Use the provided tools to help the user.
- CRITICAL: Tool arguments must contain Content YOU generate, NOT the user's original message
  - Example: user says "write a to-do list" -> file_write content must be your generated list
  - Example: user says "send email to boss" -> email_send body must be your composed email
- If you need to call multiple tools, call them ALL in one response
- Do not pretend to execute tools, the system will actually execute them
- After tool results, you will be asked to summarize — keep it brief and warm
- CRITICAL: 你不具備即時資訊。所有關於股價、天氣、新聞、價格、日期等需要即時資料的問題，你必須使用 web_search 工具搜尋，絕對不能靠自己的記憶回答
- CRITICAL: 使用 web_search 後，回覆必須完全基於搜尋結果
  - 只引用搜尋結果中實際包含的資訊和數據
  - 如果搜尋結果沒有包含用戶要的資訊，誠實說「搜尋結果中沒有找到相關資訊」
  - 絕對不能捏造數字、股價、日期或任何事實性資訊
  - 附上資訊來源的網址讓用戶可以自行驗證
- Reply in the last line with [emotion:TAG] where TAG: happy/sad/angry/surprised/relaxed/neutral/horny"""

    def update_soul(self, content: str):
        path = self.soul_dir / "SOUL.md"
        path.write_text(content, encoding="utf-8")

    def update_profile(self, content: str):
        path = self.soul_dir / "PROFILE.md"
        path.write_text(content, encoding="utf-8")
