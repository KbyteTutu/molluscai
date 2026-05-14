from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaxonRead(BaseModel):
    aphia_id: int
    scientificname: str
    authority: Optional[str]
    rank: Optional[str]
    status: Optional[str]
    valid_aphia_id: Optional[int]
    valid_name: Optional[str]
    kingdom: Optional[str]
    phylum: Optional[str]
    subphylum: Optional[str]
    class_: Optional[str] = Field(default=None, alias="class")
    subclass: Optional[str]
    infraclass: Optional[str]
    superorder: Optional[str]
    order_: Optional[str] = Field(default=None, alias="order")
    suborder: Optional[str]
    infraorder: Optional[str]
    superfamily: Optional[str]
    family: Optional[str]
    genus: Optional[str]
    species_epithet: Optional[str]
    is_marine: Optional[bool]
    is_brackish: Optional[bool]
    is_freshwater: Optional[bool]
    is_terrestrial: Optional[bool]
    is_extinct: Optional[bool]
    citation: Optional[str]
    url: Optional[str]
    data_source: str
    last_synced_at: Optional[datetime]

    model_config = {"from_attributes": True, "populate_by_name": True}


class TaxonSearchResponse(BaseModel):
    items: list[TaxonRead]
    total: int
    offset: int
    limit: int
