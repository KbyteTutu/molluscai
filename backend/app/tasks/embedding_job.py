from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@celery_app.task(
    name="taxa.embed_run",
    bind=True,
    max_retries=0,
    acks_late=True,
    time_limit=43200,
    soft_time_limit=42600,
)
def embed_run(self, rebuild: bool = False, limit: int | None = None) -> dict:
    from scripts.embed_taxa import run as taxa_run
    rc = asyncio.run(taxa_run(rebuild=rebuild, max_rows=limit))
    return {"return_code": rc, "rebuild": rebuild, "limit": limit}


@celery_app.task(name="taxa.embed_cancel", bind=True)
def embed_cancel(self) -> dict:
    from scripts.embed_taxa import request_cancel
    request_cancel()
    return {"cancelled": True}


@celery_app.task(
    name="auction.embed_run",
    bind=True,
    max_retries=0,
    acks_late=True,
    time_limit=43200,
    soft_time_limit=42600,
)
def auction_embed_run(self, rebuild: bool = False, limit: int | None = None) -> dict:
    from scripts.embed_auctions import run as auction_run
    rc = asyncio.run(auction_run(rebuild=rebuild, max_rows=limit))
    return {"return_code": rc, "rebuild": rebuild, "limit": limit}


@celery_app.task(name="auction.embed_cancel", bind=True)
def auction_embed_cancel(self) -> dict:
    from scripts.embed_auctions import request_cancel
    request_cancel()
    return {"cancelled": True}
