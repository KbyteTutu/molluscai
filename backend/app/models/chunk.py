import uuid
from datetime import datetime
from typing import Optional, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, func, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TextChunk(Base):
    __tablename__ = "text_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    page_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(3584), nullable=True
    )
    taxa: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    chunk_idx: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(
        "Document", back_populates="text_chunks"
    )

    def __repr__(self) -> str:
        return f"<TextChunk(id={self.id}, doc_id={self.doc_id}, chunk_idx={self.chunk_idx})>"


class ImageChunk(Base):
    __tablename__ = "image_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    page_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    figure_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    taxa: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(3584), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(
        "Document", back_populates="image_chunks"
    )

    def __repr__(self) -> str:
        return f"<ImageChunk(id={self.id}, doc_id={self.doc_id}, figure_type={self.figure_type})>"
