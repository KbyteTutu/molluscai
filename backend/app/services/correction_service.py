from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correction import Correction
from app.schemas.correction import CorrectionCreate


async def create_correction(
    db: AsyncSession,
    user_id: UUID,
    payload: CorrectionCreate,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Correction:
    correction = Correction(
        user_id=user_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        target_title=payload.target_title,
        field_name=payload.field_name,
        current_value=payload.current_value,
        suggested_value=payload.suggested_value,
        note=payload.note,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(correction)
    await db.commit()
    await db.refresh(correction)
    return correction


async def list_user_corrections(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Correction], int]:
    base = select(Correction).where(Correction.user_id == user_id)
    count_q = select(func.count(Correction.id)).where(Correction.user_id == user_id)

    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(
        base.order_by(Correction.created_at.desc()).limit(limit).offset(offset)
    )).scalars().all()
    return list(rows), int(total)


async def list_all_corrections(
    db: AsyncSession,
    *,
    status_filter: Optional[str] = None,
    target_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Correction], int]:
    base = select(Correction)
    count_base = select(func.count(Correction.id))

    if status_filter:
        base = base.where(Correction.status == status_filter)
        count_base = count_base.where(Correction.status == status_filter)
    if target_type:
        base = base.where(Correction.target_type == target_type)
        count_base = count_base.where(Correction.target_type == target_type)

    total = (await db.execute(count_base)).scalar_one()
    rows = (await db.execute(
        base.order_by(Correction.created_at.desc()).limit(limit).offset(offset)
    )).scalars().all()
    return list(rows), int(total)


async def get_correction(db: AsyncSession, correction_id: int) -> Optional[Correction]:
    result = await db.execute(
        select(Correction).where(Correction.id == correction_id)
    )
    return result.scalar_one_or_none()


async def get_correction_for_update(
    db: AsyncSession, correction_id: int
) -> Optional[Correction]:
    result = await db.execute(
        select(Correction)
        .where(Correction.id == correction_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()
