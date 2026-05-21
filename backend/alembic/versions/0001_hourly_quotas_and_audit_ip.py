"""Add hourly quotas + AI quotas + query log IP/status_code (P5).

Revision ID: 0001_hourly_quotas
Revises:
Create Date: 2026-05-21
"""
from alembic import op


revision = "0001_hourly_quotas"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE role_quotas
            ADD COLUMN IF NOT EXISTS hourly_ai_limit       INT NOT NULL DEFAULT -1,
            ADD COLUMN IF NOT EXISTS hourly_auction_limit  INT NOT NULL DEFAULT -1,
            ADD COLUMN IF NOT EXISTS hourly_taxa_limit     INT NOT NULL DEFAULT -1,
            ADD COLUMN IF NOT EXISTS daily_ai_limit        INT NOT NULL DEFAULT -1,
            ADD COLUMN IF NOT EXISTS daily_taxa_limit      INT NOT NULL DEFAULT -1;
    """)

    op.execute("""
        UPDATE role_quotas SET
            hourly_ai_limit = CASE role
                WHEN 'user' THEN 10
                WHEN 'vip'  THEN 100
                ELSE -1
            END,
            daily_ai_limit = CASE role
                WHEN 'user' THEN 50
                WHEN 'vip'  THEN 500
                ELSE -1
            END;
    """)

    op.execute("""
        ALTER TABLE query_logs
            ADD COLUMN IF NOT EXISTS ip_address  INET,
            ADD COLUMN IF NOT EXISTS status_code SMALLINT DEFAULT 200;
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_user_created
            ON query_logs (user_id, created_at DESC) WHERE user_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_query_logs_type_created
            ON query_logs (query_type, created_at DESC);
    """)

    op.execute("""
        ALTER TABLE query_logs DROP CONSTRAINT IF EXISTS query_logs_user_id_fkey;
        ALTER TABLE query_logs
            ADD CONSTRAINT query_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE query_logs DROP CONSTRAINT IF EXISTS query_logs_user_id_fkey;
        ALTER TABLE query_logs
            ADD CONSTRAINT query_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id);
    """)
    op.execute("DROP INDEX IF EXISTS idx_query_logs_type_created;")
    op.execute("DROP INDEX IF EXISTS idx_query_logs_user_created;")
    op.execute("""
        ALTER TABLE query_logs
            DROP COLUMN IF EXISTS status_code,
            DROP COLUMN IF EXISTS ip_address;
    """)
    op.execute("""
        ALTER TABLE role_quotas
            DROP COLUMN IF EXISTS daily_taxa_limit,
            DROP COLUMN IF EXISTS daily_ai_limit,
            DROP COLUMN IF EXISTS hourly_taxa_limit,
            DROP COLUMN IF EXISTS hourly_auction_limit,
            DROP COLUMN IF EXISTS hourly_ai_limit;
    """)
