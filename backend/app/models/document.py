import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    journal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    taxa_mentioned: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    higher_taxa: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    geographic_scope: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    content_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    doc_category: Mapped[str] = mapped_column(String(30), nullable=False)
    ocr_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    text_chunks: Mapped[List["TextChunk"]] = relationship(
        "TextChunk", back_populates="document", lazy="selectin"
    )
    image_chunks: Mapped[List["ImageChunk"]] = relationship(
        "ImageChunk", back_populates="document", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, status={self.status})>"
