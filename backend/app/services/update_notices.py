from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting


UPDATE_NOTICES_KEY = "update_notices"


class UpdateNoticeItem(BaseModel):
    date: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=80)
    text: str = Field(..., min_length=1, max_length=200)


class UpdateNoticeList(BaseModel):
    items: list[UpdateNoticeItem] = Field(default_factory=list, max_length=20)


DEFAULT_UPDATE_NOTICES = UpdateNoticeList(items=[
    UpdateNoticeItem(
        date="2026-07-07",
        title="匿名检索开放",
        text="未登录也可使用拍卖与物种词法查询。",
    ),
    UpdateNoticeItem(
        date="2026-07-07",
        title="匿名访问限流",
        text="匿名搜索每分钟 20 次，登录后可继续使用。",
    ),
    UpdateNoticeItem(
        date="2026-07-07",
        title="安全加固",
        text="模型密钥加密存储，生产弱密钥会阻止启动。",
    ),
])


def serialize_update_notices(notices: UpdateNoticeList) -> str:
    return notices.model_dump_json()


def parse_update_notices(raw: str | None) -> UpdateNoticeList:
    if not raw:
        return DEFAULT_UPDATE_NOTICES
    try:
        data: Any = json.loads(raw)
        if isinstance(data, list):
            data = {"items": data}
        return UpdateNoticeList.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return DEFAULT_UPDATE_NOTICES


async def get_update_notices(db: AsyncSession) -> UpdateNoticeList:
    row = await db.execute(select(Setting).where(Setting.key == UPDATE_NOTICES_KEY))
    setting = row.scalar_one_or_none()
    return parse_update_notices(setting.value if setting else None)


async def set_update_notices(db: AsyncSession, notices: UpdateNoticeList) -> UpdateNoticeList:
    await db.execute(
        text("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (:key, :value, now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
        """),
        {"key": UPDATE_NOTICES_KEY, "value": serialize_update_notices(notices)},
    )
    await db.commit()
    return notices
