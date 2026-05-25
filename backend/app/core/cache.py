"""Redis-backed response cache with configurable TTL.

Usage::

    from app.core.cache import cached

    @router.get("/stats")
    async def stats(db=Depends(get_db)):
        return await cached("admin:stats", ttl=60, compute=lambda: _heavy_query(db))

Cache keys are scoped by prefix; POST/PATCH handlers call `bust("admin:stats")`
to invalidate.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, TypeVar

import redis.asyncio as aioredis

from app.config import settings

log = logging.getLogger(__name__)

T = TypeVar("T")

_pool: aioredis.ConnectionPool | None = None

CACHE_PREFIX = "cache"


def _get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL, max_connections=5, decode_responses=True
        )
    return aioredis.Redis(connection_pool=_pool)


def _key(scope: str, suffix: str | None = None) -> str:
    k = f"{CACHE_PREFIX}:{scope}"
    return f"{k}:{suffix}" if suffix else k


async def get(scope: str, suffix: str | None = None) -> dict | None:
    """Return cached dict or None."""
    r = _get_redis()
    raw = await r.get(_key(scope, suffix))
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            await r.delete(_key(scope, suffix))
    return None


async def set(scope: str, data: dict, ttl: int, suffix: str | None = None) -> None:
    r = _get_redis()
    await r.setex(_key(scope, suffix), ttl, json.dumps(data, default=str))


async def bust(scope: str) -> int:
    """Delete all keys under a scope. Returns count deleted."""
    r = _get_redis()
    pattern = f"{CACHE_PREFIX}:{scope}*"
    keys = await r.keys(pattern)
    if keys:
        return await r.delete(*keys)
    return 0


async def cached(
    scope: str,
    ttl: int,
    compute: Callable[[], Awaitable[dict]],
    suffix: str | None = None,
) -> dict:
    """Get from cache or compute and store.

    Args:
        scope: Cache scope key (e.g. 'admin:stats')
        ttl: Seconds before expiry
        compute: Async callable returning a JSON-serializable dict
        suffix: Optional sub-key for parameterized caches
    """
    hit = await get(scope, suffix)
    if hit is not None:
        return hit
    data = await compute()
    if data is not None:
        asyncio.ensure_future(set(scope, data, ttl, suffix))
    return data
