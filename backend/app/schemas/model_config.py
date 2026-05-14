from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
    is_active: bool = True


class ModelConfigUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_id: Optional[str] = None
    price_input: Optional[Decimal] = None
    price_output: Optional[Decimal] = None
    price_unit: Optional[str] = None
    is_active: Optional[bool] = None


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
    api_key_tail: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelTestResponse(BaseModel):
    success: bool
    latency_ms: Optional[int] = None
    message: Optional[str] = None
    sample_dim: Optional[int] = None


class ModelUsageSummary(BaseModel):
    model_config_id: Optional[int] = None
    model_name: str
    purpose: str
    calls: int
    input_tokens: int
    total_tokens: int
    cost: Decimal
    avg_latency_ms: Optional[int] = None


class RecentUsageRow(BaseModel):
    id: int
    model_name: str
    purpose: str
    input_tokens: Optional[int]
    cost: Decimal
    latency_ms: Optional[int]
    status: str
    error_message: Optional[str]
    created_at: datetime
