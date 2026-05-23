from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuctionEmbedding(Base):
    __tablename__ = "auction_embeddings"

    item_no: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False
    )
    model_name: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False
    )
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(HALFVEC(2000), nullable=False)
    text_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<AuctionEmbedding(item_no={self.item_no}, model={self.model_name})>"
        )
