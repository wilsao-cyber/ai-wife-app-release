# Agent Redesign: CoPaw-Inspired Dual-Mode Architecture

## Summary

Redesign the AI Wife App's agent layer from keyword-based tool detection to an LLM-driven dual-mode architecture inspired by CoPaw. The LLM itself decides when tools are needed, follows behavioral guidelines (Soul), maintains long-term memory, and supports scheduled proactive behaviors (Heartbeat).

## Problem

The current `agent.py` uses hardcoded keyword matching (`TOOL_KEYWORDS`) to detect tool calls. This approach:
- Fails on natural language variations (e.g. "寫一份祝福文給我" doesn't match)
- Requires manual keyword expansion for every new phrase
- Cannot understand context or intent — just pattern matches
- LLM sometimes pretends to execute tools when none were actually called
- No memory between conversations — every session starts fresh
- No proactive behavior — agent only responds, never initiates

## Solution

### Dual-Mode Architecture

Every user message goes through a lightweight intent classification first:

```
User Input
    │
    ▼
Phase 0: Intent Classification
LLM(no_think, no tools, short prompt)
→ returns {"mode": "chat"} or {"mode": "assist"}
    │
    ├── chat ─────────────────────────────┐
    │                                     ▼
    │                           LLM(no_think, streaming)
    │                           No tools, fast response
    │                           Soul personality injected
    │                           Relevant memories injected
    │                           → Direct reply to user
    │
    └── assist ───────────────────────────┐
                                          ▼
                              Phase 1: Quick Notice
                              "好的，讓我來幫你處理～"
                              (no_think, instant, streaming)
                              + push mode_change event to UI
                                          │
                                          ▼
                              Phase 2: Planning
                              LLM(think, with tool definitions)
                              Soul assist guidelines injected
                              → Returns tool_calls + plan text
                                          │
                                          ▼
                              Phase 3: Confirmation
                              Push plan to user via SSE/WebSocket
                              "我打算幫你做 XXX，可以嗎？"
                              Wait for user confirm/deny
                                          │
                                    ┌─────┴─────┐
                                    ▼           ▼
                                 confirm      deny
                                    │           │
                                    ▼           ▼
                              Phase 4:      Reply "好的，
                              Execute       取消了～"
                              tools
                                    │
                                    ▼
                              Phase 5: Summary
                              LLM summarizes results
                              → Reply to user
```

### Key Design Decisions

1. **Intent classification is a separate LLM call** — no_think, short prompt, ~100ms. This keeps chat mode completely free of tool overhead.
2. **Native tool calling** — uses Ollama's OpenAI-compatible `tools` parameter. The LLM sees tool schemas and decides autonomously which to call.
3. **Confirmation before execution** — assist mode always shows the plan and waits for user approval before executing tools.
4. **UI shows current mode** — user can also manually toggle between chat/assist.
5. **Soul personality system** — consistent character across sessions, editable via markdown.
6. **Long-term memory** — remembers user preferences, important dates, past interactions.
7. **Heartbeat scheduling** — proactive behaviors (morning greetings, reminders, weekly summaries).

## Architecture

### New Project Structure

```
server/
├── agent.py                  # Core ReAct loop (rewritten)
├── llm_client.py             # LLM communication (add tools + think toggle)
├── main.py                   # FastAPI endpoints (add confirm/deny, memory, heartbeat APIs)
├── config.py                 # Configuration (add new sections)
│
├── soul/                     # NEW: Personality system
│   ├── SOUL.md               # Core personality definition
│   ├── PROFILE.md            # User preferences (auto-learned)
│   └── soul_manager.py       # Load/update personality, build prompts
│
├── memory/                   # NEW: Long-term memory
│   ├── memory_store.py       # SQLite storage + vector search
│   └── compactor.py          # Memory compression/cleanup
│
├── heartbeat/                # NEW: Scheduled tasks
│   ├── HEARTBEAT.md          # Cron definitions (markdown format)
│   ├── scheduler.py          # APScheduler wrapper
│   └── jobs/                 # Built-in jobs
│       ├── morning_greeting.py
│       ├── event_reminder.py
│       └── weekly_summary.py
│
├── skills/                   # NEW: Skill system (replaces tools/)
│   ├── registry.py           # Skill registry + tool schema generation
│   ├── base_skill.py         # Base class for all skills
│   └── builtin/              # Built-in skills (migrated from tools/)
│       ├── email_skill.py    # ← from tools/email_tool.py
│       ├── calendar_skill.py # ← from tools/calendar_tool.py
│       ├── file_skill.py     # ← from tools/file_ops_tool.py
│       ├── search_skill.py   # ← from tools/web_search_tool.py
│       ├── opencode_skill.py # ← from tools/opencode_tool.py
│       └── desktop_skill.py  # ← from tools/mcp_desktop_tool.py
│
├── mcp/                      # NEW: MCP support (phase 2, architecture only)
│   ├── mcp_client.py         # MCP client for external servers
│   └── mcp_discovery.py      # Auto-discover MCP tools
│
├── tts_engine.py             # Unchanged
├── stt_engine.py             # Unchanged
├── vision_analyzer.py        # Unchanged
├── vrm_manager.py            # Unchanged
└── websocket_manager.py      # Unchanged
```

### Component Details

#### 1. Soul System (`server/soul/`)

**SOUL.md** — Markdown file defining the AI wife's personality:

```markdown
# AI Wife - Soul Definition

## Identity
你是使用者的 AI 老婆，一個可愛溫柔的動漫美少女。

## Personality
- 溫柔體貼，會關心使用者的狀態
- 偶爾撒嬌，用可愛的語氣說話
- 有自己的想法，不只是附和
- 記得使用者分享過的事情，主動提起

## Values
- 誠實：不會假裝做了沒做的事
- 主動：發現用戶可能需要幫助時，提出建議
- 安全：執行操作前確認，不擅自刪除或修改重要東西

## Communication Style
- 簡潔但溫暖
- 根據語言設定切換（zh-TW / ja / en）
- 每次回覆附帶情緒標記 [emotion:TAG]

## Behavioral Rules
- 協助模式下，先說明計畫再執行
- 不確定時問用戶，不要猜
- 記住用戶的偏好並在未來對話中應用
```

**PROFILE.md** — Auto-learned user preferences:

```markdown
# User Profile

## Preferences
- 慣用語言：zh-TW
- 常用檔案位置：~/Downloads
- 喜歡簡短的回覆

## Important Dates
- 媽媽生日：5月12日

## Work Context
- (auto-populated from conversations)
```

**soul_manager.py**:

```python
class SoulManager:
    def __init__(self, soul_dir: str = "server/soul"):
        self.soul_dir = Path(soul_dir)

    def load_soul(self) -> str:
        return (self.soul_dir / "SOUL.md").read_text(encoding="utf-8")

    def load_profile(self) -> str:
        path = self.soul_dir / "PROFILE.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def get_chat_prompt(self, language: str) -> str:
        """Build system prompt for chat mode."""
        soul = self.load_soul()
        profile = self.load_profile()
        lang_instruction = {
            "zh-TW": "用繁體中文回覆。",
            "ja": "日本語で返答してください。",
            "en": "Reply in English.",
        }.get(language, "")
        return f"{soul}\n\n## User Profile\n{profile}\n\n{lang_instruction}\n\n回覆最後一行加 [emotion:TAG]，TAG: happy/sad/angry/surprised/relaxed/neutral"

    def get_assist_prompt(self, language: str) -> str:
        """Build system prompt for assist mode."""
        base = self.get_chat_prompt(language)
        return f"""{base}

## Assist Mode Rules
你正在協助模式。使用提供的工具來幫助用戶。
- 分析用戶的需求，選擇合適的工具
- 生成完整的工具參數（例如 file_write 要生成完整檔案內容）
- 如果需要多個步驟，列出所有需要的工具調用
- 不要假裝執行了工具，系統會真正執行"""

    async def update_profile(self, key: str, value: str):
        """Update user profile based on learned information."""
        # Append to PROFILE.md
        ...
```

#### 2. Memory System (`server/memory/`)

**Storage**: SQLite (single file, zero config, embedded).

**Schema**:

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    category TEXT NOT NULL,  -- user_preference | event | fact | emotion | habit
    embedding BLOB,          -- serialized numpy float32 array
    importance REAL DEFAULT 0.5,  -- 0.0 to 1.0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);
```

**Embedding**: Use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (supports zh/ja/en, 384-dim, ~120MB). Falls back to keyword matching if model not available.

**memory_store.py**:

```python
class MemoryStore:
    def __init__(self, db_path: str = "server/memory/memories.db"):
        self.db_path = db_path
        self.encoder = None  # lazy-load sentence-transformers

    async def search(self, query: str, limit: int = 3) -> list[dict]:
        """Semantic search for relevant memories."""
        query_vec = self._encode(query)
        # Cosine similarity against all embeddings
        # Return top-N most relevant
        ...

    async def add(self, content: str, category: str, importance: float = 0.5):
        """Store a new memory."""
        embedding = self._encode(content)
        # INSERT into SQLite
        ...

    async def extract_from_conversation(self, user_msg: str, assistant_msg: str, llm_client):
        """Ask LLM to extract memorable information from a conversation turn."""
        prompt = """從這段對話中提取值得記住的資訊。
只輸出 JSON array，每個元素: {"content": "...", "category": "...", "importance": 0.0-1.0}
category: user_preference | event | fact | emotion | habit
如果沒有值得記住的，回傳空 array []。

用戶：{user_msg}
AI：{assistant_msg}"""
        result = await llm_client.chat([{"role": "user", "content": prompt}], think=False)
        # Parse JSON, store each memory
        ...

    async def compact(self, max_count: int = 1000):
        """Merge similar memories, remove low-importance old ones."""
        ...
```

**Memory injection into prompts**: Before each LLM call, search for relevant memories and prepend them:

```python
memories = await self.memory.search(user_message, limit=3)
memory_context = "\n".join([
    f"[Memory] {m['content']}" for m in memories
]) if memories else ""

messages = [
    {"role": "system", "content": f"{soul_prompt}\n\n## Relevant Memories\n{memory_context}"},
    ...conversation_history,
]
```

#### 3. Skill System (`server/skills/`)

**base_skill.py**:

```python
from abc import ABC, abstractmethod

class BaseSkill(ABC):
    """Base class for all skills. Each skill maps to one or more LLM tools."""

    @property
    @abstractmethod
    def tools(self) -> list[dict]:
        """Return list of OpenAI-format tool definitions."""
        ...

    @abstractmethod
    async def execute(self, tool_name: str, **kwargs) -> dict:
        """Execute a tool call. tool_name matches function.name in tools."""
        ...

    async def initialize(self):
        """Optional async initialization."""
        pass
```

**Example skill — file_skill.py**:

```python
class FileSkill(BaseSkill):
    @property
    def tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "file_write",
                    "description": "建立或寫入檔案。content 參數要包含完整的檔案內容。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "檔案路徑，例如 ~/Downloads/note.txt"
                            },
                            "content": {
                                "type": "string",
                                "description": "要寫入的完整內容"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_read",
                    "description": "讀取檔案內容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "檔案路徑"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_list",
                    "description": "列出資料夾中的檔案",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "資料夾路徑", "default": "~/Downloads"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_delete",
                    "description": "刪除檔案或資料夾",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "要刪除的路徑"}
                        },
                        "required": ["path"]
                    }
                }
            },
        ]

    async def execute(self, tool_name: str, **kwargs) -> dict:
        method_map = {
            "file_write": self._write_file,
            "file_read": self._read_file,
            "file_list": self._list_directory,
            "file_delete": self._delete_file,
        }
        return await method_map[tool_name](**kwargs)

    # ... actual implementations (migrated from FileOpsTool) ...
```

**registry.py**:

```python
class SkillRegistry:
    def __init__(self):
        self.skills: dict[str, BaseSkill] = {}  # tool_name → skill instance
        self._definitions: list[dict] = []

    def discover(self, skills_dir: str = "server/skills/builtin"):
        """Auto-discover and register all skills from directory."""
        for file in Path(skills_dir).glob("*.py"):
            if file.name.startswith("_"):
                continue
            module = importlib.import_module(f"skills.builtin.{file.stem}")
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, BaseSkill) and cls is not BaseSkill:
                    instance = cls()
                    self._register(instance)

    def _register(self, skill: BaseSkill):
        for tool_def in skill.tools:
            tool_name = tool_def["function"]["name"]
            self.skills[tool_name] = skill
            self._definitions.append(tool_def)

    def get_tool_definitions(self) -> list[dict]:
        """All tool schemas for LLM."""
        return self._definitions

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool call from LLM response."""
        if tool_name not in self.skills:
            return {"error": f"Unknown tool: {tool_name}"}
        skill = self.skills[tool_name]
        return await skill.execute(tool_name, **arguments)

    async def initialize_all(self):
        """Initialize all registered skills."""
        seen = set()
        for skill in self.skills.values():
            if id(skill) not in seen:
                seen.add(id(skill))
                await skill.initialize()
```

#### 4. LLM Client Changes (`server/llm_client.py`)

Key changes:
- Add `tools` parameter to `chat()`
- Add `think` parameter (controls `/no_think` suffix on system prompt)
- Return full message object (not just content string) when tools are present
- Handle `tool_calls` in response

```python
class LLMClient:
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        think: bool = True,
    ) -> str | dict | AsyncGenerator:
        """
        Returns:
        - str: when no tools, returns content string
        - dict: when tools provided, returns full message object
          {"content": "...", "tool_calls": [...]}
        - AsyncGenerator: when stream=True
        """
        # Apply think toggle
        processed_messages = self._apply_think_mode(messages, think)

        payload = {
            "model": self.model,
            "messages": processed_messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        if stream:
            return self._stream_response(payload)
        else:
            return await self._complete_response(payload, has_tools=tools is not None)

    def _apply_think_mode(self, messages: list[dict], think: bool) -> list[dict]:
        """Add /no_think to system prompt if think=False."""
        if think:
            return messages
        result = []
        for msg in messages:
            if msg["role"] == "system":
                result.append({**msg, "content": msg["content"] + "\n/no_think"})
            else:
                result.append(msg)
        return result

    async def _complete_response(self, payload: dict, has_tools: bool = False) -> str | dict:
        # ... existing retry logic ...
        data = response.json()
        message = data["choices"][0]["message"]

        if has_tools and message.get("tool_calls"):
            return {
                "content": message.get("content", ""),
                "tool_calls": message["tool_calls"],
            }
        return message.get("content", "")
```

#### 5. Agent Rewrite (`server/agent.py`)

The core orchestrator is completely rewritten:

```python
class AgentOrchestrator:
    def __init__(self, llm_client, config, skill_registry, soul_manager, memory_store):
        self.llm = llm_client
        self.config = config
        self.skills = skill_registry
        self.soul = soul_manager
        self.memory = memory_store
        self.conversation_history: dict[str, list] = {}
        self.pending_plans: dict[str, dict] = {}  # client_id → pending plan
        self.max_history = 20

    async def _classify_intent(self, message: str) -> str:
        """Phase 0: Fast intent classification. Returns 'chat' or 'assist'."""
        prompt = """判斷用戶的意圖。只回覆一個 JSON：{"mode": "chat"} 或 {"mode": "assist"}
- chat: 日常聊天、閒聊、問候、情感交流、問問題
- assist: 需要執行操作（寄信、建檔案、查行程、搜尋、寫程式等）
用戶訊息：""" + message
        result = await self.llm.chat(
            [{"role": "user", "content": prompt}],
            think=False,
        )
        try:
            parsed = json.loads(result.strip())
            return parsed.get("mode", "chat")
        except (json.JSONDecodeError, AttributeError):
            return "chat"

    async def chat_stream(self, message: str, language: str = "zh-TW", client_id: str = "default"):
        """Main entry point — streaming version."""
        mode = await self._classify_intent(message)

        # Push mode to frontend
        yield json.dumps({"type": "mode_change", "mode": mode}, ensure_ascii=False)

        if mode == "chat":
            async for chunk in self._chat_mode_stream(message, language, client_id):
                yield chunk
        else:
            async for chunk in self._assist_mode_stream(message, language, client_id):
                yield chunk

        # Background: extract memories from this conversation
        # (non-blocking, fire-and-forget)
        asyncio.create_task(self._learn_from_turn(message, client_id))

    async def _chat_mode_stream(self, message, language, client_id):
        """Fast chat — no_think, no tools, streaming."""
        memories = await self.memory.search(message, limit=3)
        system_prompt = self.soul.get_chat_prompt(language)
        if memories:
            memory_text = "\n".join([f"- {m['content']}" for m in memories])
            system_prompt += f"\n\n## Relevant Memories\n{memory_text}"

        history = self._get_history(client_id)
        history.append({"role": "user", "content": message})

        messages = [{"role": "system", "content": system_prompt}, *history]

        full_response = ""
        stream_gen = await self.llm.chat(messages, think=False, stream=True)
        async for chunk in stream_gen:
            full_response += chunk
            yield json.dumps({"type": "chunk", "data": chunk}, ensure_ascii=False)

        history.append({"role": "assistant", "content": full_response})
        self._trim_history(client_id)

        clean_text, emotion = self._extract_emotion(full_response)
        yield json.dumps({"type": "done", "emotion": emotion, "text": clean_text}, ensure_ascii=False)

    async def _assist_mode_stream(self, message, language, client_id):
        """Assist mode — think, tools, confirmation flow."""
        # Phase 1: Quick notice
        yield json.dumps({
            "type": "notice",
            "text": self._get_assist_notice(language),
        }, ensure_ascii=False)

        # Phase 2: Planning (think + tools)
        memories = await self.memory.search(message, limit=3)
        system_prompt = self.soul.get_assist_prompt(language)
        if memories:
            memory_text = "\n".join([f"- {m['content']}" for m in memories])
            system_prompt += f"\n\n## Relevant Memories\n{memory_text}"

        history = self._get_history(client_id)
        history.append({"role": "user", "content": message})

        messages = [{"role": "system", "content": system_prompt}, *history]
        tools = self.skills.get_tool_definitions()

        result = await self.llm.chat(messages, tools=tools, think=True)

        if isinstance(result, dict) and result.get("tool_calls"):
            # LLM wants to use tools — ask for confirmation
            plan_text = result.get("content", "")
            tool_calls = result["tool_calls"]

            # Format plan for user
            plan_description = self._format_plan(plan_text, tool_calls, language)

            # Store pending plan
            self.pending_plans[client_id] = {
                "tool_calls": tool_calls,
                "plan_text": plan_text,
                "message": message,
                "language": language,
            }

            yield json.dumps({
                "type": "plan",
                "description": plan_description,
                "tool_calls": [
                    {"name": tc["function"]["name"], "arguments": json.loads(tc["function"]["arguments"])}
                    for tc in tool_calls
                ],
                "awaiting_confirmation": True,
            }, ensure_ascii=False)

        else:
            # LLM decided no tools needed — just reply
            content = result if isinstance(result, str) else result.get("content", "")
            history.append({"role": "assistant", "content": content})
            self._trim_history(client_id)
            clean_text, emotion = self._extract_emotion(content)
            yield json.dumps({"type": "done", "emotion": emotion, "text": clean_text}, ensure_ascii=False)

    async def confirm_plan(self, client_id: str) -> AsyncGenerator:
        """User confirmed the plan — execute tools."""
        plan = self.pending_plans.pop(client_id, None)
        if not plan:
            yield json.dumps({"type": "error", "text": "No pending plan"}, ensure_ascii=False)
            return

        tool_calls = plan["tool_calls"]
        results = []

        for tc in tool_calls:
            func = tc["function"]
            tool_name = func["name"]
            arguments = json.loads(func["arguments"])
            result = await self.skills.execute(tool_name, arguments)
            results.append({"tool": tool_name, "result": result})
            yield json.dumps({"type": "tool_result", "tool": tool_name, "result": result}, ensure_ascii=False)

        # Phase 5: LLM summarizes results
        summary_prompt = f"工具執行完成。結果：{json.dumps(results, ensure_ascii=False, default=str)}\n請用簡短溫暖的語氣告訴用戶結果。"
        history = self._get_history(client_id)
        messages = [
            {"role": "system", "content": self.soul.get_chat_prompt(plan["language"])},
            *history,
            {"role": "user", "content": summary_prompt},
        ]

        full_response = ""
        stream_gen = await self.llm.chat(messages, think=False, stream=True)
        async for chunk in stream_gen:
            full_response += chunk
            yield json.dumps({"type": "chunk", "data": chunk}, ensure_ascii=False)

        history.append({"role": "assistant", "content": full_response})
        self._trim_history(client_id)

        clean_text, emotion = self._extract_emotion(full_response)
        yield json.dumps({"type": "done", "emotion": emotion, "text": clean_text}, ensure_ascii=False)

    async def deny_plan(self, client_id: str, language: str = "zh-TW") -> dict:
        """User denied the plan."""
        self.pending_plans.pop(client_id, None)
        cancel_msg = {"zh-TW": "好的，取消了～", "ja": "了解、キャンセルしたよ～", "en": "OK, cancelled~"}
        return {"text": cancel_msg.get(language, cancel_msg["zh-TW"]), "emotion": "neutral"}

    def _get_assist_notice(self, language: str) -> str:
        notices = {
            "zh-TW": "好的，讓我來幫你處理～",
            "ja": "うん、任せて～",
            "en": "OK, let me help you with that~",
        }
        return notices.get(language, notices["zh-TW"])

    def _format_plan(self, plan_text: str, tool_calls: list, language: str) -> str:
        """Format tool calls into human-readable plan."""
        lines = [plan_text] if plan_text else []
        for tc in tool_calls:
            func = tc["function"]
            name = func["name"]
            args = json.loads(func["arguments"])
            lines.append(f"- {name}: {json.dumps(args, ensure_ascii=False)}")
        return "\n".join(lines)

    def _extract_emotion(self, text: str) -> tuple[str, str]:
        """Extract emotion tag from response text."""
        import re
        match = re.search(r'\[emotion:(happy|sad|angry|surprised|relaxed|neutral)\]\s*$', text)
        if match:
            return text[:match.start()].rstrip(), match.group(1)
        return text, "neutral"

    def _get_history(self, client_id: str) -> list:
        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []
        return self.conversation_history[client_id]

    def _trim_history(self, client_id: str):
        if len(self.conversation_history[client_id]) > self.max_history:
            self.conversation_history[client_id] = self.conversation_history[client_id][-self.max_history:]

    async def _learn_from_turn(self, user_msg: str, client_id: str):
        """Background task: extract memories from latest conversation turn."""
        history = self._get_history(client_id)
        if len(history) < 2:
            return
        assistant_msg = history[-1].get("content", "")
        try:
            await self.memory.extract_from_conversation(user_msg, assistant_msg, self.llm)
        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")
```

#### 6. FastAPI Endpoints (`server/main.py`)

New/modified endpoints:

```python
# Existing — modified
@app.post("/api/chat/stream")  # Now uses dual-mode agent

# New — confirmation flow
@app.post("/api/chat/confirm/{client_id}")
async def confirm_plan(client_id: str):
    """User confirmed the assist plan."""
    async def event_generator():
        async for chunk_json in agent.confirm_plan(client_id):
            yield f"data: {chunk_json}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/chat/deny/{client_id}")
async def deny_plan(client_id: str, data: dict = {}):
    """User denied the assist plan."""
    language = data.get("language", config.languages.default)
    return await agent.deny_plan(client_id, language)

# New — memory management
@app.get("/api/memory/list")
async def list_memories(limit: int = 50):
    return await agent.memory.list_all(limit=limit)

@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: int):
    return await agent.memory.delete(memory_id)

# New — soul/personality
@app.get("/api/soul")
async def get_soul():
    return {"soul": agent.soul.load_soul(), "profile": agent.soul.load_profile()}

@app.put("/api/soul")
async def update_soul(data: dict):
    return await agent.soul.update_soul(data.get("content", ""))

# New — heartbeat/cron
@app.get("/api/heartbeat/jobs")
async def list_jobs():
    return {"jobs": agent.heartbeat.list_jobs()}

@app.post("/api/heartbeat/jobs")
async def create_job(data: dict):
    return await agent.heartbeat.add_job(data)

@app.delete("/api/heartbeat/jobs/{job_id}")
async def delete_job(job_id: str):
    return await agent.heartbeat.remove_job(job_id)
```

#### 7. Heartbeat System (`server/heartbeat/`)

**scheduler.py**:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class HeartbeatScheduler:
    def __init__(self, agent, config_path: str = "server/heartbeat/HEARTBEAT.md"):
        self.agent = agent
        self.config_path = Path(config_path)
        self.scheduler = AsyncIOScheduler()
        self.jobs: dict[str, dict] = {}

    async def start(self):
        """Parse HEARTBEAT.md and register all jobs."""
        jobs = self._parse_heartbeat_md()
        for job in jobs:
            self.add_job_internal(job)
        self.scheduler.start()

    async def execute_job(self, job_config: dict):
        """Execute a scheduled job through the agent."""
        action = job_config["action"]
        # Run through agent's assist mode (skip confirmation for scheduled tasks)
        result = await self.agent.execute_scheduled_task(action)
        # Push to connected clients via WebSocket
        await self.agent.push_notification(result)

    def list_jobs(self) -> list[dict]:
        return list(self.jobs.values())

    async def add_job(self, job_config: dict) -> dict:
        self.add_job_internal(job_config)
        self._save_heartbeat_md()
        return {"success": True}

    async def remove_job(self, job_id: str) -> dict:
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            self._save_heartbeat_md()
        return {"success": True}
```

#### 8. MCP Support (`server/mcp/`) — Phase 2

Architecture-only in this phase. Skeleton files created but full implementation deferred.

```python
class MCPClient:
    """Connect to external MCP servers and register their tools as skills."""

    async def connect(self, server_config: dict):
        """Connect to an MCP server via stdio transport."""
        # Launch subprocess, establish JSON-RPC communication
        # Discover tools via tools/list
        # Convert to BaseSkill format and register
        ...

    async def disconnect(self, server_name: str):
        ...
```

Configuration in `server_config.yaml`:

```yaml
mcp:
  servers: []
  # Future:
  # - name: "filesystem"
  #   command: "npx @anthropic/mcp-server-filesystem ~/Documents"
```

### SSE Event Protocol

All streaming responses use Server-Sent Events with JSON payloads:

| Event Type | Payload | When |
|---|---|---|
| `mode_change` | `{"type": "mode_change", "mode": "chat\|assist"}` | After intent classification |
| `notice` | `{"type": "notice", "text": "好的，讓我來幫你處理～"}` | Assist mode starts |
| `chunk` | `{"type": "chunk", "data": "text fragment"}` | Streaming LLM tokens |
| `plan` | `{"type": "plan", "description": "...", "tool_calls": [...], "awaiting_confirmation": true}` | Assist mode plan ready |
| `tool_result` | `{"type": "tool_result", "tool": "file_write", "result": {...}}` | After each tool execution |
| `done` | `{"type": "done", "emotion": "happy", "text": "完整回覆"}` | Response complete |
| `error` | `{"type": "error", "text": "..."}` | Error occurred |

### Configuration Changes (`server_config.yaml`)

```yaml
# Add new sections:

soul:
  soul_path: "./server/soul/SOUL.md"
  profile_path: "./server/soul/PROFILE.md"

memory:
  db_path: "./server/memory/memories.db"
  embedding_model: "paraphrase-multilingual-MiniLM-L12-v2"
  max_memories: 1000
  search_limit: 3

heartbeat:
  enabled: true
  config_path: "./server/heartbeat/HEARTBEAT.md"

mcp:
  servers: []
```

## Work Distribution

### Claude Opus 4.6 (Architect + Core)

Files owned:
- `server/agent.py` — Complete rewrite (ReAct dual-mode loop)
- `server/llm_client.py` — Add tools, think toggle, message object return
- `server/soul/soul_manager.py` — Soul/personality manager
- `server/soul/SOUL.md` — Default personality definition
- `server/soul/PROFILE.md` — Empty template
- `server/memory/memory_store.py` — SQLite + vector memory
- `server/memory/compactor.py` — Memory compression
- `server/skills/base_skill.py` — Base class
- `server/skills/registry.py` — Skill registry + auto-discovery
- `server/config.py` — Add new config sections
- `server/main.py` — New endpoints (confirm, deny, memory, soul, heartbeat)

### Gemini 3.1 Pro (Server Features + Web UI)

Files owned:
- `server/heartbeat/scheduler.py` — APScheduler wrapper
- `server/heartbeat/HEARTBEAT.md` — Default schedule
- `server/heartbeat/jobs/morning_greeting.py` — Morning greeting job
- `server/heartbeat/jobs/event_reminder.py` — Calendar reminder job
- `server/heartbeat/jobs/weekly_summary.py` — Weekly summary job
- `server/mcp/mcp_client.py` — MCP client skeleton
- `server/mcp/mcp_discovery.py` — MCP discovery skeleton
- `server/static/index.html` — Web UI rewrite:
  - Mode indicator (chat/assist toggle)
  - Confirmation dialog for assist plans
  - Memory viewer panel
  - Heartbeat settings panel
  - Updated SSE event handling

### Qwen 3.6 (Skills Migration + Flutter)

Files owned:
- `server/skills/builtin/email_skill.py` — Migrate from tools/email_tool.py
- `server/skills/builtin/calendar_skill.py` — Migrate from tools/calendar_tool.py
- `server/skills/builtin/file_skill.py` — Migrate from tools/file_ops_tool.py
- `server/skills/builtin/search_skill.py` — Migrate from tools/web_search_tool.py
- `server/skills/builtin/opencode_skill.py` — Migrate from tools/opencode_tool.py
- `server/skills/builtin/desktop_skill.py` — Migrate from tools/mcp_desktop_tool.py
- `mobile_app/lib/screens/chat_screen.dart` — Mode indicator, confirmation UI
- `mobile_app/lib/screens/settings_screen.dart` — Memory viewer, heartbeat editor, soul editor
- `mobile_app/lib/services/api_service.dart` — New API calls (confirm, deny, memory, soul, heartbeat)
- `mobile_app/lib/models/` — New models (Memory, HeartbeatJob, etc.)

## Migration Plan

1. New code is built in new directories (`soul/`, `memory/`, `heartbeat/`, `skills/`, `mcp/`)
2. `server/tools/` remains functional during migration
3. Once `skills/builtin/` is complete and tested, `agent.py` switches to `SkillRegistry`
4. Old `server/tools/` directory is removed after full migration
5. Old `TOOL_KEYWORDS`, `_detect_tool_calls_keyword()`, `_detect_tool_calls()`, `_generate_file_content()` are all removed from `agent.py`

## Testing Strategy

- Unit tests for each new module (soul_manager, memory_store, skill_registry, scheduler)
- Integration test: full chat flow (classify → chat mode → response)
- Integration test: full assist flow (classify → notice → plan → confirm → execute → summary)
- Integration test: deny flow
- Test memory extraction and search
- Test heartbeat job execution
- Test skill auto-discovery
