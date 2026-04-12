import logging
import aiosqlite

logger = logging.getLogger(__name__)


class MemoryCompactor:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def compact(self, max_count: int = 5000):
        """Remove low-importance, old, rarely-accessed memories when count exceeds max.
        Protects high-importance (>= 0.8) and frequently-accessed (>= 5) memories."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM memories") as cursor:
                row = await cursor.fetchone()
                count = row[0]

            if count <= max_count:
                return 0

            to_remove = count - max_count
            # Only remove memories with low importance AND low access count
            # This protects important memories and frequently recalled ones
            await db.execute(
                """DELETE FROM memories WHERE id IN (
                    SELECT id FROM memories
                    WHERE importance < 0.8 AND access_count < 5
                    ORDER BY importance ASC, access_count ASC, created_at ASC
                    LIMIT ?
                )""",
                (to_remove,),
            )
            await db.commit()

            # Check how many were actually removed
            async with db.execute("SELECT COUNT(*) FROM memories") as cursor:
                new_count = (await cursor.fetchone())[0]
            removed = count - new_count
            logger.info(f"Compacted {removed} memories (was {count}, now {new_count})")
            return removed
