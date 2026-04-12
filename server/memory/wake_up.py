"""Wake-up Context Manager (L0/L1)

Provides persistent identity and key facts that are injected into every conversation,
so the AI always knows who the user is without needing memory search.

L0 — Identity Core (~50 tokens): user name, relationship basics, core preferences.
     Sourced from PROFILE.md and high-importance fact memories.
     Updated when profile changes or important new facts are learned.

L1 — Key Facts (~120 tokens): recent emotional state, current concerns, important events.
     Updated periodically by the daily_reflection heartbeat job.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WakeUpManager:
    def __init__(self, memory_dir: str = "./server/memory"):
        self._dir = Path(memory_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._l0_path = self._dir / "L0_identity.md"
        self._l1_path = self._dir / "L1_facts.md"
        self._l0_cache: str = ""
        self._l1_cache: str = ""

    async def initialize(self):
        """Load L0 and L1 from disk."""
        self._l0_cache = self._read_file(self._l0_path)
        self._l1_cache = self._read_file(self._l1_path)
        logger.info(
            f"Wake-up context loaded: L0={len(self._l0_cache)} chars, "
            f"L1={len(self._l1_cache)} chars"
        )

    def get_context(self) -> str:
        """Return combined L0 + L1 text for injection into system prompt."""
        parts = []
        if self._l0_cache:
            parts.append(self._l0_cache)
        if self._l1_cache:
            parts.append(self._l1_cache)
        return "\n\n".join(parts)

    @property
    def has_context(self) -> bool:
        return bool(self._l0_cache or self._l1_cache)

    # ── L0: Identity Core ───────────────────────────────────────────

    async def update_l0(self, content: str):
        """Update L0 identity core. Called when profile changes or important facts emerge."""
        self._l0_cache = content.strip()
        self._write_file(self._l0_path, self._l0_cache)
        logger.info(f"L0 identity updated ({len(self._l0_cache)} chars)")

    async def build_l0_from_memories(self, memory_store, llm_client):
        """Auto-build L0 from high-importance fact memories and profile."""
        try:
            # Get top fact memories by importance
            import aiosqlite
            facts = []
            async with aiosqlite.connect(memory_store.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT content FROM memories "
                    "WHERE category = 'fact' AND importance >= 0.7 "
                    "ORDER BY importance DESC, access_count DESC "
                    "LIMIT 10"
                ) as cursor:
                    facts = [row["content"] async for row in cursor]

            if not facts:
                logger.info("No high-importance facts found for L0")
                return

            prompt = (
                "你是一個記憶整理助手。根據以下關於用戶的事實資訊，"
                "寫一段簡短的身份摘要（50字以內），包含：\n"
                "- 用戶的稱呼/名字\n"
                "- 與AI的關係（AI是他的妻子「小愛」）\n"
                "- 最重要的1-2個核心偏好\n\n"
                "事實：\n" + "\n".join(f"- {f}" for f in facts) + "\n\n"
                "只輸出摘要文字，不要解釋。用繁體中文。"
            )

            result = await llm_client.chat(
                [{"role": "user", "content": prompt}],
                think=False, max_tokens=200, temperature=0.3,
            )
            if result and isinstance(result, str):
                await self.update_l0(result.strip())
        except Exception as e:
            logger.warning(f"Failed to build L0: {e}")

    # ── L1: Key Facts ───────────────────────────────────────────────

    async def update_l1(self, content: str):
        """Update L1 key facts. Called by daily_reflection heartbeat."""
        self._l1_cache = content.strip()
        self._write_file(self._l1_path, self._l1_cache)
        logger.info(f"L1 facts updated ({len(self._l1_cache)} chars)")

    async def build_l1_from_memories(self, memory_store, llm_client):
        """Auto-build L1 by summarizing recent and important memories."""
        try:
            import aiosqlite

            # Get recent memories (last 7 days) + high importance ones
            memories = []
            async with aiosqlite.connect(memory_store.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT content, category, importance, created_at FROM memories "
                    "WHERE created_at >= datetime('now', '-7 days') "
                    "   OR importance >= 0.8 "
                    "ORDER BY created_at DESC "
                    "LIMIT 30"
                ) as cursor:
                    memories = [
                        {"content": row["content"], "category": row["category"],
                         "importance": row["importance"]}
                        async for row in cursor
                    ]

            if not memories:
                logger.info("No recent memories found for L1")
                return

            mem_text = "\n".join(
                f"- [{m['category']}] {m['content']}" for m in memories
            )
            prompt = (
                "你是一個記憶整理助手。根據以下近期記憶，"
                "寫一段簡短的近況摘要（120字以內），包含：\n"
                "- 用戶最近的情緒狀態\n"
                "- 用戶最近在關心/忙碌的事\n"
                "- 近期發生的重要事件\n"
                "- 需要注意的日期或事項\n\n"
                f"記憶：\n{mem_text}\n\n"
                "只輸出摘要文字，不要解釋。用繁體中文。"
            )

            result = await llm_client.chat(
                [{"role": "user", "content": prompt}],
                think=False, max_tokens=300, temperature=0.3,
            )
            if result and isinstance(result, str):
                await self.update_l1(result.strip())
        except Exception as e:
            logger.warning(f"Failed to build L1: {e}")

    # ── File helpers ────────────────────────────────────────────────

    @staticmethod
    def _read_file(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8").strip() if path.exists() else ""
        except Exception:
            return ""

    @staticmethod
    def _write_file(path: Path, content: str):
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write {path}: {e}")
