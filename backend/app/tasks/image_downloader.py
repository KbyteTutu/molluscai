"""
Download original auction images to MinIO for sold lots (todo.md requirement #5).

Only sold auctions are persisted long-term; the source site can purge listings.
Idempotent: skips objects already present in the bucket; updates images_local on success.
"""
import asyncio
import logging
from typing import List, Optional
from urllib.parse import urljoin

import aiohttp
import asyncpg

from app.config import settings
from app.services.minio_client import ensure_bucket, get_minio, object_exists, put_bytes
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

BUCKET = "auction-images"
SITE_BASE = "https://shellauction.net/"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MalacoAgent/0.1; +https://malacoagent.local)"
}


def _candidate_paths(raw: str) -> List[str]:
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    return [p for p in parts if not p.endswith(".gif")]


def _object_name(item_no: int, idx: int, src: str) -> str:
    ext = src.rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        ext = "jpg"
    return f"{item_no // 10000:04d}/{item_no}_{idx}.{ext}"


async def _fetch_and_store(session: aiohttp.ClientSession, item_no: int, idx: int, src: str) -> Optional[str]:
    obj_name = _object_name(item_no, idx, src)
    if object_exists(BUCKET, obj_name):
        return f"{BUCKET}/{obj_name}"
    url = urljoin(SITE_BASE, src.lstrip("/"))
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning("image %s HTTP %s", url, resp.status)
                return None
            data = await resp.read()
            ctype = resp.headers.get("Content-Type", "image/jpeg")
    except Exception as e:
        logger.warning("image %s fetch failed: %s", url, e)
        return None
    return put_bytes(BUCKET, obj_name, data, ctype)


async def _process_batch(rows) -> dict:
    ensure_bucket(BUCKET)
    pool = await asyncpg.create_pool(settings.DATABASE_URL_SYNC)
    downloaded = 0
    updated = 0
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT, headers=HEADERS) as session:
            for row in rows:
                item_no = row["item_no"]
                origins = row["images_origin"] or []
                local_paths: List[str] = []
                for raw in origins:
                    for idx, src in enumerate(_candidate_paths(raw)):
                        stored = await _fetch_and_store(session, item_no, idx, src)
                        if stored:
                            local_paths.append(stored)
                            downloaded += 1
                if local_paths:
                    await pool.execute(
                        "UPDATE auctions SET images_local = $1 WHERE item_no = $2",
                        local_paths,
                        item_no,
                    )
                    updated += 1
    finally:
        await pool.close()
    return {"downloaded": downloaded, "updated": updated, "batch_size": len(rows)}


async def _pick_sold_without_local(limit: int):
    conn = await asyncpg.connect(settings.DATABASE_URL_SYNC)
    try:
        rows = await conn.fetch(
            """
            SELECT item_no, images_origin
            FROM auctions
            WHERE is_sold = true
              AND images_origin IS NOT NULL
              AND (images_local IS NULL OR cardinality(images_local) = 0)
            ORDER BY end_date DESC NULLS LAST
            LIMIT $1
            """,
            limit,
        )
        return rows
    finally:
        await conn.close()


@celery_app.task(name="auction.download_images", bind=True)
def download_sold_images(self, batch_size: int = 50) -> dict:
    """Pick up to `batch_size` sold auctions missing local images and download them."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        rows = loop.run_until_complete(_pick_sold_without_local(batch_size))
        if not rows:
            return {"downloaded": 0, "updated": 0, "batch_size": 0}
        result = loop.run_until_complete(_process_batch(rows))
        logger.info("download_sold_images result: %s", result)
        return result
    finally:
        loop.close()
