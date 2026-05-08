from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ModelConfigCreate(BaseModel):
    model_name: str
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model_id: Optional[str] = None
    purpose: str
    price_input: Optional[Decimal] = None
    price_output: Optional[Decimal] = None
    price_unit: str = "per_1k_tokens"


class ModelConfigRead(BaseModel):
    id: int
    model_name: str
    provider: str
    base_url: Optional[str]
    model_id: Optional[str]
    purpose: str
    price_input: Optional[Decimal]
    price_output: Optional[Decimal]
    price_unit: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
