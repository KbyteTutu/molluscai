from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TaxonMatchInfo(BaseModel):
    kind: Literal["name", "synonym", "vernacular"]
    term: str
    authority: Optional[str] = None
    language: Optional[str] = None


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
    match_info: Optional[TaxonMatchInfo] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class TaxonSearchResponse(BaseModel):
    items: list[TaxonRead]
    total: int
    offset: int
    limit: int


class TaxonSynonym(BaseModel):
    synonym_aphia_id: int
    scientificname: str
    authority: Optional[str]
    status: Optional[str]


class TaxonVernacular(BaseModel):
    vernacular: str
    language_code: Optional[str]


class TaxonDistribution(BaseModel):
    locality: Optional[str]
    higher_geography: Optional[str]
    establishment_means: Optional[str]
    decimal_latitude: Optional[float]
    decimal_longitude: Optional[float]
    quality_status: Optional[str]


class TaxonChild(BaseModel):
    child_aphia_id: int
    scientificname: Optional[str]
    rank: Optional[str]
    status: Optional[str]


class TaxonClassificationStep(BaseModel):
    ancestor_aphia_id: int
    scientificname: str
    rank: Optional[str]
    depth: int


class TaxonExternalId(BaseModel):
    source: str
    external_id: str
