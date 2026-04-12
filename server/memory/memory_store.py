import logging
import json
import re
import aiosqlite
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(
        self, db_path: str = "server/memory/memories.db", use_embeddings: bool = True
    ):
        self.db_path = db_path
        self.use_embeddings = use_embeddings
        self._encoder = None

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    embedding BLOB,
                    importance REAL DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    wing TEXT DEFAULT 'general',
                    room TEXT DEFAULT 'misc'
                )
            """)
            # Migration: add wing/room columns to existing DBs
            try:
                await db.execute("ALTER TABLE memories ADD COLUMN wing TEXT DEFAULT 'general'")
            except Exception:
                pass  # Column already exists
            try:
                await db.execute("ALTER TABLE memories ADD COLUMN room TEXT DEFAULT 'misc'")
            except Exception:
                pass  # Column already exists
            await db.commit()

        if self.use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer

                self._encoder = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
                logger.info("Embedding model loaded for memory search")
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed, falling back to keyword search"
                )
                self.use_embeddings = False

    def _encode(self, text: str) -> Optional[bytes]:
        if self._encoder is None:
            return None
        import numpy as np

        vec = self._encoder.encode(text, normalize_embeddings=True)
        return vec.astype(np.float32).tobytes()

    async def add(
        self, content: str, category: str, importance: float = 0.5,
        wing: str = "general", room: str = "misc",
    ):
        embedding = self._encode(content)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO memories (content, category, embedding, importance, wing, room) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (content, category, embedding, importance, wing, room),
            )
            await db.commit()

    async def search(
        self, query: str, limit: int = 3, wing: Optional[str] = None,
    ) -> list[dict]:
        if self.use_embeddings and self._encoder is not None:
            return await self._search_vector(query, limit, wing=wing)
        return await self._search_keyword(query, limit, wing=wing)

    async def _search_vector(
        self, query: str, limit: int, wing: Optional[str] = None,
    ) -> list[dict]:
        import numpy as np

        query_vec = self._encoder.encode(query, normalize_embeddings=True).astype(
            np.float32
        )

        results = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if wing:
                sql = "SELECT * FROM memories WHERE embedding IS NOT NULL AND wing = ?"
                params = (wing,)
            else:
                sql = "SELECT * FROM memories WHERE embedding IS NOT NULL"
                params = ()
            async with db.execute(sql, params) as cursor:
                async for row in cursor:
                    mem_vec = np.frombuffer(row["embedding"], dtype=np.float32)
                    score = float(np.dot(query_vec, mem_vec))
                    results.append({**dict(row), "score": score, "embedding": None})

        results.sort(key=lambda x: x["score"], reverse=True)
        top = results[:limit]

        for m in top:
            await self.update_access(m["id"])

        return top

    async def _search_keyword(
        self, query: str, limit: int, wing: Optional[str] = None,
    ) -> list[dict]:
        words = query.lower().split()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if wing:
                sql = "SELECT * FROM memories WHERE wing = ? ORDER BY importance DESC, created_at DESC"
                params = (wing,)
            else:
                sql = "SELECT * FROM memories ORDER BY importance DESC, created_at DESC"
                params = ()
            async with db.execute(sql, params) as cursor:
                all_mems = [dict(row) async for row in cursor]

        scored = []
        for mem in all_mems:
            content_lower = mem["content"].lower()
            score = sum(1 for w in words if w in content_lower)
            if score > 0:
                mem["score"] = score
                mem["embedding"] = None
                scored.append(mem)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    async def list_all(self, limit: int = 50) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, content, category, importance, created_at, last_accessed, access_count "
                "FROM memories ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def delete(self, memory_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            await db.commit()

    async def update_access(self, memory_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                (datetime.now().isoformat(), memory_id),
            )
            await db.commit()

    async def count(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM memories") as cursor:
                row = await cursor.fetchone()
                return row[0]

    VALID_WINGS = {"relationship", "work", "daily", "interest", "health", "general"}

    async def extract_from_conversation(
        self, user_msg: str, assistant_msg: str, llm_client
    ):
        prompt = f"""從這段對話中提取值得記住的資訊。
只輸出 JSON array，每個元素: {{"content": "...", "category": "...", "wing": "...", "room": "...", "importance": 0.0-1.0}}
category 必須是: user_preference | event | fact | emotion | habit
wing 必須是: relationship（感情相關）| work（工作相關）| daily（日常生活）| interest（興趣愛好）| health（健康相關）| general（其他）
room 是 wing 下的子主題，自由命名（例如 anniversary, diet, project_x, gaming 等）
如果沒有值得記住的，回傳空 array []
不要輸出任何其他文字。

用戶：{user_msg}
AI：{assistant_msg}"""
        try:
            result = await llm_client.chat(
                [{"role": "user", "content": prompt}], think=False
            )
            cleaned = result.strip()
            code_block = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
            if code_block:
                cleaned = code_block.group(1)
            elif cleaned.find("[") >= 0:
                cleaned = cleaned[cleaned.find("[") : cleaned.rfind("]") + 1]
            elif cleaned.find("{") >= 0:
                cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]
            memories = json.loads(cleaned)
            if not isinstance(memories, list):
                return
            for mem in memories:
                if isinstance(mem, dict) and "content" in mem and "category" in mem:
                    wing = mem.get("wing", "general")
                    if wing not in self.VALID_WINGS:
                        wing = "general"
                    await self.add(
                        content=mem["content"],
                        category=mem["category"],
                        importance=float(mem.get("importance", 0.5)),
                        wing=wing,
                        room=mem.get("room", "misc"),
                    )
                    logger.info(
                        f"Memory extracted [{wing}/{mem.get('room', 'misc')}]: "
                        f"{mem['content'][:50]}..."
                    )
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Memory extraction failed: {e}")
