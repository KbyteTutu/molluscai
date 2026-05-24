from __future__ import annotations
import logging
from datetime import datetime, timezone
import asyncpg

log = logging.getLogger(__name__)


class EmbeddingTaskService:
    @staticmethod
    async def create(
        conn: asyncpg.Connection,
        celery_task_id: str | None,
        task_type: str,
        rebuild: bool,
        limit_rows: int | None,
    ) -> int:
        row = await conn.fetchrow(
            """INSERT INTO embedding_tasks (celery_task_id, task_type, state, rebuild, limit_rows)
               VALUES ($1, $2, 'running', $3, $4)
               RETURNING id""",
            celery_task_id, task_type, rebuild, limit_rows,
        )
        return row["id"]

    @staticmethod
    async def update_state(
        conn: asyncpg.Connection,
        task_id: int,
        state: str,
        error_message: str | None = None,
        total_count: int | None = None,
    ) -> None:
        await conn.execute(
            """UPDATE embedding_tasks
               SET state = $2, error_message = COALESCE($3, error_message),
                   total_count = COALESCE($4, total_count),
                   updated_at = $5,
                   completed_at = CASE WHEN $2 IN ('completed', 'failed', 'cancelled') THEN $5 ELSE completed_at END
               WHERE id = $1""",
            task_id, state, error_message, total_count,
            datetime.now(timezone.utc),
        )

    @staticmethod
    async def save_checkpoint(
        conn: asyncpg.Connection,
        task_id: int,
        checkpoint_id: int,
        total_processed: int,
    ) -> None:
        await conn.execute(
            """UPDATE embedding_tasks
               SET last_checkpoint_id = $2, total_processed = $3, updated_at = $4
               WHERE id = $1""",
            task_id, checkpoint_id, total_processed, datetime.now(timezone.utc),
        )

    @staticmethod
    async def get_checkpoint(
        conn: asyncpg.Connection,
        task_id: int,
    ) -> tuple[int | None, int]:
        row = await conn.fetchrow(
            "SELECT last_checkpoint_id, total_processed FROM embedding_tasks WHERE id = $1",
            task_id,
        )
        if row is None:
            return None, 0
        return row["last_checkpoint_id"], row["total_processed"]

    @staticmethod
    async def get_latest_task(
        conn: asyncpg.Connection,
        task_type: str,
    ) -> dict | None:
        row = await conn.fetchrow(
            "SELECT * FROM embedding_tasks WHERE task_type = $1 ORDER BY id DESC LIMIT 1",
            task_type,
        )
        return dict(row) if row else None
