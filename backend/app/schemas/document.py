from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: str
    title: Optional[str]
    authors: Optional[List[str]]
    year: Optional[int]
    journal: Optional[str]
    doi: Optional[str]
    abstract: Optional[str]
    content_type: Optional[str]
    doc_category: str
    status: str
    total_pages: Optional[int]
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    id: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    items: List[DocumentRead]
    total: int
    offset: int
    limit: int
