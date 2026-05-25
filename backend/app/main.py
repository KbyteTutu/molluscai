from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.api.v1 import admin, auction, auth, corrections, feedback, models as models_api, taxa, users
from app.core.exceptions import register_exception_handlers


async def bootstrap_app_settings() -> None:
    """Ensure app_settings table and default rows exist.

    Idempotent: safe to run on every startup. Covers environments where the
    Postgres init SQL did not run (e.g. existing data volume on upgrade).
    """
    from app.database import engine

    async with engine.begin() as conn:
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
app.include_router(models_api.router, prefix="/api/v1/admin/models", tags=["Admin"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(corrections.router, prefix="/api/v1", tags=["Corrections"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
