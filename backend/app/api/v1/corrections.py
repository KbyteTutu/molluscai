import re
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.request_ip import get_client_ip
from app.models.user import User
from app.schemas.correction import CorrectionCreate, CorrectionOut
from app.services.correction_service import create_correction, list_user_corrections

router = APIRouter()

CORRECTION_RATE_LIMIT = 20

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitize(text: str) -> str:
    return _CONTROL_RE.sub("", text)


def _serialize(c: "Correction") -> CorrectionOut:
    return CorrectionOut(
        id=c.id,
        user_id=str(c.user_id) if c.user_id else "",
        target_type=c.target_type,
        target_id=c.target_id,
        target_title=c.target_title,
        field_name=c.field_name,
        current_value=c.current_value,
        suggested_value=c.suggested_value,
        note=c.note,
        status=c.status,
        admin_note=c.admin_note,
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )


@router.post("/corrections", response_model=CorrectionOut, status_code=status.HTTP_201_CREATED)
async def submit_correction(
    payload: CorrectionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.models.correction import Correction

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    count_row = await db.execute(
        select(func.count(Correction.id)).where(
            Correction.user_id == current_user.id,
            Correction.created_at >= since,
        )
    )
    if count_row.scalar_one() >= CORRECTION_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"纠错提交过于频繁，每24小时最多 {CORRECTION_RATE_LIMIT} 条",
        )

    if payload.note:
        payload.note = _sanitize(payload.note)
    payload.suggested_value = _sanitize(payload.suggested_value)
    if payload.current_value:
        payload.current_value = _sanitize(payload.current_value)

    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")[:1024] if request.headers.get("user-agent") else None

    correction = await create_correction(
        db=db,
        user_id=current_user.id,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
    )
    return _serialize(correction)


@router.get("/corrections/me", response_model=List[CorrectionOut])
async def list_my_corrections(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    items, _ = await list_user_corrections(
        db=db, user_id=current_user.id, limit=limit, offset=offset
    )
    return [_serialize(c) for c in items]
