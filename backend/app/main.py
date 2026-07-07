from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.api.v1 import admin, auction, auth, corrections, feedback, models as models_api, public, taxa, users
from app.core.exceptions import register_exception_handlers
from app.services.update_notices import DEFAULT_UPDATE_NOTICES, UPDATE_NOTICES_KEY, serialize_update_notices


async def bootstrap_app_settings() -> None:
    """Ensure upgrade-time database compatibility objects exist.

    Idempotent: safe to run on every startup. Covers environments where the
    Postgres init SQL did not run (e.g. existing data volume on upgrade).
    """
    from app.database import engine

    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE role_quotas
                ADD COLUMN IF NOT EXISTS hourly_ai_limit       INT NOT NULL DEFAULT -1,
                ADD COLUMN IF NOT EXISTS hourly_auction_limit  INT NOT NULL DEFAULT -1,
                ADD COLUMN IF NOT EXISTS hourly_taxa_limit     INT NOT NULL DEFAULT -1,
                ADD COLUMN IF NOT EXISTS daily_ai_limit        INT NOT NULL DEFAULT -1,
                ADD COLUMN IF NOT EXISTS daily_taxa_limit      INT NOT NULL DEFAULT -1
        """))
        await conn.execute(text("""
            ALTER TABLE query_logs
                ADD COLUMN IF NOT EXISTS ip_address  INET,
                ADD COLUMN IF NOT EXISTS status_code SMALLINT DEFAULT 200
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_query_logs_user_created
                ON query_logs (user_id, created_at DESC) WHERE user_id IS NOT NULL
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_query_logs_type_created
                ON query_logs (query_type, created_at DESC)
        """))
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint c
                    JOIN pg_class t ON t.oid = c.conrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
                    WHERE t.relname = 'query_logs'
                      AND c.contype = 'f'
                      AND a.attname = 'user_id'
                ) THEN
                    ALTER TABLE query_logs
                        ADD CONSTRAINT query_logs_user_id_fkey
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
                END IF;
            END $$
        """))
        await conn.execute(text("""
            ALTER TABLE taxa_vernaculars ADD COLUMN IF NOT EXISTS source TEXT
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS taxa_inaturalist (
                aphia_id              INTEGER PRIMARY KEY REFERENCES taxa(aphia_id) ON DELETE CASCADE,
                inat_id               INTEGER,
                found                 BOOLEAN NOT NULL DEFAULT TRUE,
                preferred_common_name TEXT,
                observations_count    INTEGER,
                wikipedia_url         TEXT,
                wikipedia_summary     TEXT,
                image_url             TEXT,
                conservation_status   TEXT,
                raw                   JSONB,
                synced_at             TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS taxon_name_zh (
                latin_name   TEXT PRIMARY KEY,
                chinese_name TEXT NOT NULL,
                rank_type    TEXT NOT NULL
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_taxon_name_zh_rank ON taxon_name_zh (rank_type)
        """))
        await conn.execute(text("""
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
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_embedding_tasks_celery_task_id
                ON embedding_tasks (celery_task_id)
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        await conn.execute(text("""
            INSERT INTO app_settings (key, value) VALUES
              ('smart_search_auction', 'false'),
              ('smart_search_taxa', 'true'),
              ('smart_search_documents', 'false')
            ON CONFLICT (key) DO NOTHING
        """))
        await conn.execute(
            text("""
                INSERT INTO app_settings (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key) DO NOTHING
            """),
            {
                "key": UPDATE_NOTICES_KEY,
                "value": serialize_update_notices(DEFAULT_UPDATE_NOTICES),
            },
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    await bootstrap_app_settings()
    yield
    # Shutdown
    from app.database import engine
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(auction.router, prefix="/api/v1/auction", tags=["Auction"])
app.include_router(taxa.router, prefix="/api/v1/taxa", tags=["Taxa"])
app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
app.include_router(models_api.router, prefix="/api/v1/admin/models", tags=["Admin"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(corrections.router, prefix="/api/v1", tags=["Corrections"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
