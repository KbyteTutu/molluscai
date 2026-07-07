from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.update_notices import UpdateNoticeList, get_update_notices

router = APIRouter()


@router.get("/update-notices", response_model=UpdateNoticeList)
async def public_update_notices(
    db: AsyncSession = Depends(get_db),
):
    return await get_update_notices(db)
