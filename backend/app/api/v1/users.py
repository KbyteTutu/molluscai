from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.quota import (
    ALL_QUERY_TYPES,
    QuotaSnapshot,
    QuotaWindow,
    get_user_quota_snapshot,
)
from app.models.user import User

router = APIRouter()


class QuotaWindowOut(BaseModel):
    used: int
    limit: int
    remaining: int
    reset_at: str

    @classmethod
    def from_window(cls, w: QuotaWindow) -> "QuotaWindowOut":
        return cls(
            used=w.used,
            limit=w.limit,
            remaining=w.remaining,
            reset_at=w.reset_at.isoformat(),
        )


class QuotaTypeOut(BaseModel):
    query_type: str
    hourly: QuotaWindowOut
    daily: QuotaWindowOut

    @classmethod
    def from_snapshot(cls, s: QuotaSnapshot) -> "QuotaTypeOut":
        return cls(
            query_type=s.query_type,
            hourly=QuotaWindowOut.from_window(s.hourly),
            daily=QuotaWindowOut.from_window(s.daily),
        )


class QuotaResponse(BaseModel):
    role: str
    quotas: dict[str, QuotaTypeOut]


@router.get("/me/quota", response_model=QuotaResponse)
async def get_my_quota(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotas: dict[str, QuotaTypeOut] = {}
    for qt in ALL_QUERY_TYPES:
        snapshot = await get_user_quota_snapshot(db, current_user, qt)
        quotas[qt] = QuotaTypeOut.from_snapshot(snapshot)
    return QuotaResponse(role=current_user.role, quotas=quotas)
