from __future__ import annotations

import logging
from dataclasses import dataclass

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from app.config import settings
from app.core.request_ip import get_client_ip

log = logging.getLogger(__name__)

ANONYMOUS_SEARCH_LIMIT_PER_MINUTE = 20
ANONYMOUS_SEARCH_WINDOW_SECONDS = 60

_pool: aioredis.ConnectionPool | None = None


@dataclass(frozen=True)
class AnonymousRateLimitResult:
    ip_address: str | None
    allowed: bool
    used: int
    limit: int
    retry_after_seconds: int


def _redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL, max_connections=5, decode_responses=True
        )
    return aioredis.Redis(connection_pool=_pool)


def _client_key(ip_address: str | None) -> str:
    return ip_address or "unknown"


async def check_anonymous_search_rate_limit(
    request: Request,
    *,
    limit: int = ANONYMOUS_SEARCH_LIMIT_PER_MINUTE,
    window_seconds: int = ANONYMOUS_SEARCH_WINDOW_SECONDS,
) -> AnonymousRateLimitResult:
    ip_address = get_client_ip(request)
    key = f"rate:anonymous_search:{_client_key(ip_address)}"

    try:
        redis = _redis()
        used = int(await redis.incr(key))
        if used == 1:
            await redis.expire(key, window_seconds)
        ttl = await redis.ttl(key)
        retry_after = ttl if ttl and ttl > 0 else window_seconds
    except Exception as exc:
        log.warning("anonymous search rate limiter unavailable: %s", exc)
        return AnonymousRateLimitResult(
            ip_address=ip_address,
            allowed=True,
            used=0,
            limit=limit,
            retry_after_seconds=window_seconds,
        )

    allowed = used <= limit
    return AnonymousRateLimitResult(
        ip_address=ip_address,
        allowed=allowed,
        used=used,
        limit=limit,
        retry_after_seconds=retry_after,
    )


def raise_anonymous_rate_limited(result: AnonymousRateLimitResult) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "anonymous_rate_limited",
            "message": "匿名搜索过于频繁，请登录后继续使用。",
            "limit": result.limit,
            "used": result.used,
            "window": "minute",
            "retry_after_seconds": result.retry_after_seconds,
        },
        headers={"Retry-After": str(result.retry_after_seconds)},
    )
