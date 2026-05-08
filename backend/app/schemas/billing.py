from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel


class BalanceRead(BaseModel):
    balance: Decimal
    username: str

    model_config = {"from_attributes": True}


class BillingHistoryItem(BaseModel):
    id: int
    amount: Decimal
    action_type: Optional[str]
    description: Optional[str]
    balance_after: Optional[Decimal]
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingHistoryResponse(BaseModel):
    items: List[BillingHistoryItem]
    total: int
