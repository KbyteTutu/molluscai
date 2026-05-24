"""Add embedding_tasks table for persistent task tracking.

Revision ID: 0002_embedding_tasks
Revises: 0001_hourly_quotas
Create Date: 2026-05-24
"""
from alembic import op


revision = "0002_embedding_tasks"
down_revision = "0001_hourly_quotas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS embedding_tasks (
            id                 BIGSERIAL PRIMARY KEY,
            celery_task_id     VARCHAR(255) UNIQUE,
            task_type          VARCHAR(20) NOT NULL,
            state              VARCHAR(20) NOT NULL DEFAULT 'pending',
            rebuild            BOOLEAN NOT NULL DEFAULT FALSE,
            limit_rows         INTEGER,
            last_checkpoint_id BIGINT,
            total_processed    INTEGER NOT NULL DEFAULT 0,
            total_count        INTEGER,
            error_message      TEXT,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at       TIMESTAMPTZ
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_embedding_tasks_celery_task_id
            ON embedding_tasks (celery_task_id);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_embedding_tasks_celery_task_id;")
    op.execute("DROP TABLE IF EXISTS embedding_tasks;")
