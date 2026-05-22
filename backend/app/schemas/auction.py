from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class AuctionSearchRequest(BaseModel):
    name: Optional[str] = None
    family: Optional[str] = None
    size: Optional[str] = None
    size_min: Optional[Decimal] = None
    size_max: Optional[Decimal] = None
    has_no_size: Optional[bool] = None
    locality: Optional[str] = None
    price_min: Optional[Decimal] = None
    price_max: Optional[Decimal] = None
    end_date_from: Optional[date] = None
    end_date_to: Optional[date] = None
    seller: Optional[str] = None
    is_sold: Optional[bool] = None
    sort: Optional[str] = Field(default=None, pattern="^(relevance|end_date_desc|price_desc|price_asc|item_no_desc)$")
    offset: int = Field(default=0, ge=0, le=500)
    limit: int = Field(default=10, ge=1, le=50)


class AuctionRead(BaseModel):
    id: int
    item_no: int
    name: Optional[str]
    family: Optional[str]
    size: Optional[str]
    locality: Optional[str]
    seller: Optional[str]
    start_price: Optional[Decimal]
    final_price: Optional[Decimal]
    end_date: Optional[date]
    buyer: Optional[str]
    is_sold: bool
    images_origin: Optional[List[str]] = None
    images_local: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuctionDetail(BaseModel):
    id: int
    item_no: int
    name: Optional[str]
    family: Optional[str]
    size: Optional[str]
    locality: Optional[str]
    note: Optional[str]
    seller: Optional[str]
    start_price: Optional[Decimal]
    final_price: Optional[Decimal]
    end_date: Optional[date]
    buyer: Optional[str]
    is_sold: bool
    images_local: Optional[List[str]]
    images_origin: Optional[List[str]]
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    items: List[AuctionRead]
    total: int
    offset: int
    limit: int
