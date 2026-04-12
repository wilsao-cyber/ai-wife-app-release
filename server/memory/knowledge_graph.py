"""Knowledge Graph with temporal awareness and contradiction detection.

Stores entity-relationship triples (subject, predicate, object) with validity windows.
When a new fact contradicts an existing active fact, the old one is marked as expired
and a contradiction is queued for the AI to naturally follow up on.

Example:
  (user, lives_in, 台北, valid_from=2024-01, valid_until=2025-06)
  (user, lives_in, 竹北, valid_from=2025-06, valid_until=NULL)  ← current
"""

import logging
import json
import re
import aiosqlite
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    def __init__(self, db_path: str = "server/memory/memories.db"):
        self.db_path = db_path
        self._pending_contradictions: list[dict] = []

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    valid_until TIMESTAMP,
                    source_memory_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_facts_active "
                "ON facts (subject, predicate) WHERE valid_until IS NULL"
            )
            await db.commit()
        logger.info("Knowledge Graph initialized")

    async def add_fact(
        self, subject: str, predicate: str, obj: str,
        source_memory_id: Optional[int] = None,
    ) -> Optional[dict]:
        """Add a fact triple. Returns contradiction info if one was detected, else None."""
        contradiction = None

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Check for contradicting active facts (same subject + predicate, different object)
            async with db.execute(
                "SELECT id, object, valid_from FROM facts "
                "WHERE subject = ? AND predicate = ? AND valid_until IS NULL",
                (subject, predicate),
            ) as cursor:
                existing = await cursor.fetchone()

            if existing and existing["object"] != obj:
                # Contradiction detected — expire the old fact
                old_obj = existing["object"]
                now = datetime.now().isoformat()
                await db.execute(
                    "UPDATE facts SET valid_until = ? WHERE id = ?",
                    (now, existing["id"]),
                )
                contradiction = {
                    "subject": subject,
                    "predicate": predicate,
                    "old_value": old_obj,
                    "new_value": obj,
                    "old_valid_from": existing["valid_from"],
                }
                self._pending_contradictions.append(contradiction)
                logger.info(
                    f"KG contradiction: {subject}.{predicate}: "
                    f"'{old_obj}' → '{obj}'"
                )
            elif existing and existing["object"] == obj:
                # Same fact already exists, skip
                return None

            # Insert the new fact
            await db.execute(
                "INSERT INTO facts (subject, predicate, object, source_memory_id) "
                "VALUES (?, ?, ?, ?)",
                (subject, predicate, obj, source_memory_id),
            )
            await db.commit()

        logger.info(f"KG fact added: ({subject}, {predicate}, {obj})")
        return contradiction

    async def query(
        self, subject: Optional[str] = None,
        predicate: Optional[str] = None,
        active_only: bool = True,
    ) -> list[dict]:
        """Query facts. By default returns only currently active facts."""
        conditions = []
        params = []
        if subject:
            conditions.append("subject = ?")
            params.append(subject)
        if predicate:
            conditions.append("predicate = ?")
            params.append(predicate)
        if active_only:
            conditions.append("valid_until IS NULL")

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM facts WHERE {where} ORDER BY created_at DESC"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                return [dict(row) async for row in cursor]

    async def get_user_summary(self) -> str:
        """Get a text summary of all active facts about the user."""
        facts = await self.query(subject="user", active_only=True)
        if not facts:
            return ""
        lines = [f"- {f['predicate']}: {f['object']}" for f in facts]
        return "\n".join(lines)

    def pop_contradictions(self) -> list[dict]:
        """Pop and return pending contradictions for injection into next conversation."""
        contradictions = self._pending_contradictions[:]
        self._pending_contradictions.clear()
        return contradictions

    def get_contradiction_prompt(self) -> str:
        """Build a natural prompt hint for the AI to follow up on contradictions."""
        contradictions = self.pop_contradictions()
        if not contradictions:
            return ""
        hints = []
        for c in contradictions:
            hints.append(
                f"你注意到一個變化：之前知道{c['subject']}的{c['predicate']}是"
                f"「{c['old_value']}」，但現在似乎變成了「{c['new_value']}」。"
                f"如果合適的話，可以自然地關心一下發生了什麼變化。"
            )
        return "\n".join(hints)

    async def extract_from_conversation(
        self, user_msg: str, assistant_msg: str, llm_client,
    ):
        """Extract entity-relationship triples from a conversation turn."""
        prompt = f"""從這段對話中提取關於用戶的事實三元組。
只輸出 JSON array，每個元素: {{"subject": "user", "predicate": "...", "object": "..."}}
predicate 範例: lives_in, works_at, likes, dislikes, has_pet, relationship_status, age, name, hobby, mood, health_condition
object 用簡短文字表示
如果沒有值得記錄的事實，回傳空 array []
不要輸出任何其他文字。

用戶：{user_msg}
AI：{assistant_msg}"""
        try:
            result = await llm_client.chat(
                [{"role": "user", "content": prompt}],
                think=False, max_tokens=500, temperature=0.2,
            )
            cleaned = result.strip()
            code_block = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
            if code_block:
                cleaned = code_block.group(1)
            elif cleaned.find("[") >= 0:
                cleaned = cleaned[cleaned.find("[") : cleaned.rfind("]") + 1]
            triples = json.loads(cleaned)
            if not isinstance(triples, list):
                return
            for t in triples:
                if (isinstance(t, dict) and "subject" in t
                        and "predicate" in t and "object" in t):
                    await self.add_fact(
                        subject=t["subject"],
                        predicate=t["predicate"],
                        obj=t["object"],
                    )
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"KG extraction failed: {e}")

    async def count(self, active_only: bool = True) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            where = "WHERE valid_until IS NULL" if active_only else ""
            async with db.execute(f"SELECT COUNT(*) FROM facts {where}") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
