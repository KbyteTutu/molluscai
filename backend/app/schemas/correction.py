from typing import List, Optional

from pydantic import BaseModel, Field


class CorrectionCreate(BaseModel):
    target_type: str = Field(min_length=1, max_length=50)
    target_id: str = Field(min_length=1, max_length=100)
    target_title: Optional[str] = Field(default=None, max_length=500)
    field_name: str = Field(min_length=1, max_length=100)
    current_value: Optional[str] = Field(default=None, max_length=5000)
    suggested_value: str = Field(min_length=1, max_length=5000)
    note: Optional[str] = Field(default=None, max_length=2000)


class CorrectionOut(BaseModel):
    id: int
    user_id: str
    target_type: str
    target_id: str
    target_title: Optional[str] = None
    field_name: str
    current_value: Optional[str] = None
    suggested_value: str
    note: Optional[str] = None
    status: str
    admin_note: Optional[str] = None
    created_at: str
    updated_at: str


class CorrectionAdminUpdate(BaseModel):
    status: Optional[str] = None
    admin_note: Optional[str] = None

    model_config = {"extra": "forbid"}


class AdminCorrectionOut(BaseModel):
    id: int
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    target_type: str
    target_id: str
    target_title: Optional[str] = None
    field_name: str
    current_value: Optional[str] = None
    suggested_value: str
    note: Optional[str] = None
    status: str
    admin_note: Optional[str] = None
    created_at: str
    updated_at: str


class CorrectionListOut(BaseModel):
    items: List[CorrectionOut]
    total: int


class AdminCorrectionListOut(BaseModel):
    items: List[AdminCorrectionOut]
    total: int
    limit: int
    offset: int
