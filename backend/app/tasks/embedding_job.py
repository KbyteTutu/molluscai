from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@celery_app.task(name="taxa.embed_run", bind=True)
def embed_run(self, rebuild: bool = False, limit: int | None = None) -> dict:
    from scripts.embed_taxa import run
    rc = asyncio.new_event_loop().run_until_complete(run(rebuild=rebuild, max_rows=limit))
    return {"return_code": rc, "rebuild": rebuild, "limit": limit}


@celery_app.task(name="taxa.embed_cancel", bind=True)
def embed_cancel(self) -> dict:
    from scripts.embed_taxa import request_cancel
    request_cancel()
    return {"cancelled": True}


@celery_app.task(name="auction.embed_run", bind=True)
def auction_embed_run(self, rebuild: bool = False, limit: int | None = None) -> dict:
    from scripts.embed_auctions import run
    rc = asyncio.new_event_loop().run_until_complete(run(rebuild=rebuild, max_rows=limit))
    return {"return_code": rc, "rebuild": rebuild, "limit": limit}


@celery_app.task(name="auction.embed_cancel", bind=True)
def auction_embed_cancel(self) -> dict:
    from scripts.embed_auctions import request_cancel
    request_cancel()
    return {"cancelled": True}
