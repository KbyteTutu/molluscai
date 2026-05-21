import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api.deps import get_current_user, get_db
from app.core.request_ip import get_client_ip
from app.database import get_db
from app.models.feedback import Feedback
from app.models.user import User

router = APIRouter()

ALLOWED_CATEGORIES = {"bug", "feature", "other"}
FEEDBACK_RATE_LIMIT = 5


class FeedbackCreate(BaseModel):
    category: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=5, max_length=2000)


class FeedbackOut(BaseModel):
    id: int
    category: str
    content: str
    status: str
    admin_note: Optional[str] = None
    created_at: str
    updated_at: str


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitize_content(text: str) -> str:
    """Strip control characters except \n and \t."""
    return _CONTROL_RE.sub("", text)


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Allowed: {', '.join(sorted(ALLOWED_CATEGORIES))}",
        )

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    count_row = await db.execute(
        select(func.count(Feedback.id)).where(
            Feedback.user_id == current_user.id,
            Feedback.created_at >= since,
        )
    )
    recent_count = count_row.scalar_one()
    if recent_count >= FEEDBACK_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"反馈提交过于频繁，每24小时最多 {FEEDBACK_RATE_LIMIT} 条",
        )

    sanitized = _sanitize_content(payload.content)
    if not sanitized.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content is empty after sanitization",
        )

    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")[:1024] if request.headers.get("user-agent") else None

    fb = Feedback(
        user_id=current_user.id,
        category=payload.category,
        content=sanitized,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    return _serialize(fb)


@router.get("/feedback/me", response_model=List[FeedbackOut])
async def list_my_feedback(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    rows = await db.execute(
        select(Feedback)
        .where(Feedback.user_id == current_user.id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_serialize(fb) for fb in rows.scalars().all()]


def _serialize(fb: Feedback) -> FeedbackOut:
    return FeedbackOut(
        id=fb.id,
        category=fb.category,
        content=fb.content,
        status=fb.status,
        admin_note=fb.admin_note,
        created_at=fb.created_at.isoformat() if fb.created_at else "",
        updated_at=fb.updated_at.isoformat() if fb.updated_at else "",
    )
