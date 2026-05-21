from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_ip import get_client_ip
from app.models.user import QueryLog, RoleQuota, User


QUOTA_UNLIMITED = -1

QUERY_TYPE_AI = "ai"
QUERY_TYPE_AUCTION = "auction"
QUERY_TYPE_TAXA = "taxa"

ALL_QUERY_TYPES = (QUERY_TYPE_AI, QUERY_TYPE_AUCTION, QUERY_TYPE_TAXA)


def is_over_quota(used: int, limit: int) -> bool:
    if limit == QUOTA_UNLIMITED:
        return False
    return used >= limit


@dataclass(frozen=True)
class QuotaWindow:
    used: int
    limit: int
    reset_at: datetime

    @property
    def remaining(self) -> int:
        if self.limit == QUOTA_UNLIMITED:
            return -1
        return max(0, self.limit - self.used)


@dataclass(frozen=True)
class QuotaSnapshot:
    query_type: str
    hourly: QuotaWindow
    daily: QuotaWindow


def _hourly_reset(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def _daily_reset(now: datetime) -> datetime:
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight + timedelta(days=1)


def _hourly_limit(role_quota: RoleQuota, query_type: str) -> int:
    return {
        QUERY_TYPE_AI: role_quota.hourly_ai_limit,
        QUERY_TYPE_AUCTION: role_quota.hourly_auction_limit,
        QUERY_TYPE_TAXA: role_quota.hourly_taxa_limit,
    }.get(query_type, QUOTA_UNLIMITED)


def _daily_limit(role_quota: RoleQuota, query_type: str) -> int:
    return {
        QUERY_TYPE_AI: role_quota.daily_ai_limit,
        QUERY_TYPE_AUCTION: role_quota.daily_auction_limit,
        QUERY_TYPE_TAXA: role_quota.daily_taxa_limit,
    }.get(query_type, QUOTA_UNLIMITED)


async def _get_role_quota(db: AsyncSession, role: str) -> Optional[RoleQuota]:
    result = await db.execute(select(RoleQuota).where(RoleQuota.role == role))
    return result.scalar_one_or_none()


async def _count_queries_since(
    db: AsyncSession, user_id, query_type: str, since: datetime
) -> int:
    stmt = select(func.count(QueryLog.id)).where(
        QueryLog.user_id == user_id,
        QueryLog.query_type == query_type,
        QueryLog.created_at >= since,
        QueryLog.status_code < 400,
    )
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def get_user_quota_snapshot(
    db: AsyncSession, user: User, query_type: str
) -> QuotaSnapshot:
    now = datetime.now(timezone.utc)
    role_quota = await _get_role_quota(db, user.role)
    if role_quota is None:
        h_limit = QUOTA_UNLIMITED
        d_limit = QUOTA_UNLIMITED
    else:
        h_limit = _hourly_limit(role_quota, query_type)
        d_limit = _daily_limit(role_quota, query_type)

    hour_since = now - timedelta(hours=1)
    day_since = now - timedelta(days=1)

    hour_used = (
        0 if h_limit == QUOTA_UNLIMITED
        else await _count_queries_since(db, user.id, query_type, hour_since)
    )
    day_used = (
        0 if d_limit == QUOTA_UNLIMITED
        else await _count_queries_since(db, user.id, query_type, day_since)
    )

    return QuotaSnapshot(
        query_type=query_type,
        hourly=QuotaWindow(used=hour_used, limit=h_limit, reset_at=_hourly_reset(now)),
        daily=QuotaWindow(used=day_used, limit=d_limit, reset_at=_daily_reset(now)),
    )


def _quota_payload(snapshot: QuotaSnapshot, window: str) -> dict:
    win = snapshot.hourly if window == "hourly" else snapshot.daily
    now = datetime.now(timezone.utc)
    retry_after = max(1, int((win.reset_at - now).total_seconds()))
    return {
        "error": "quota_exceeded",
        "query_type": snapshot.query_type,
        "window": window,
        "used": win.used,
        "limit": win.limit,
        "reset_at": win.reset_at.isoformat(),
        "retry_after_seconds": retry_after,
    }


def raise_quota_exceeded(snapshot: QuotaSnapshot, window: str) -> None:
    payload = _quota_payload(snapshot, window)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=payload,
        headers={"Retry-After": str(payload["retry_after_seconds"])},
    )


async def _acquire_quota_lock(
    db: AsyncSession, user_id, query_type: str
) -> None:
    key = f"{user_id}:{query_type}"
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
        {"k": key},
    )


async def check_quota(
    db: AsyncSession,
    user: User,
    query_type: str,
    *,
    request: Optional[Request] = None,
    query_text: str = "",
) -> QuotaSnapshot:
    await _acquire_quota_lock(db, user.id, query_type)
    snapshot = await get_user_quota_snapshot(db, user, query_type)

    over_hourly = is_over_quota(snapshot.hourly.used, snapshot.hourly.limit)
    over_daily = is_over_quota(snapshot.daily.used, snapshot.daily.limit)

    if over_hourly or over_daily:
        ip = get_client_ip(request) if request is not None else None
        await log_query(
            db,
            user=user,
            query_type=query_type,
            query_text=query_text or f"<rate-limited {query_type}>",
            result_count=0,
            ip_address=ip,
            status_code=429,
        )
        raise_quota_exceeded(snapshot, "hourly" if over_hourly else "daily")

    return snapshot


async def log_query(
    db: AsyncSession,
    *,
    user: Optional[User],
    query_type: str,
    query_text: str,
    result_count: Optional[int] = None,
    cost: Decimal = Decimal("0.0000"),
    ip_address: Optional[str] = None,
    status_code: int = 200,
) -> None:
    truncated = (query_text or "")[:500]
    log = QueryLog(
        user_id=user.id if user else None,
        query_text=truncated,
        query_type=query_type,
        result_count=result_count,
        cost=cost,
        ip_address=ip_address,
        status_code=status_code,
    )
    db.add(log)
    await db.commit()


def extract_ip(request: Request) -> Optional[str]:
    return get_client_ip(request)
