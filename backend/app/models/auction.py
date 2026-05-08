from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Boolean, Date, DateTime, Integer, Numeric, String, Text, Computed, func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_no: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    family: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    size: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seller: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    final_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    buyer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_sold: Mapped[bool] = mapped_column(
        Boolean,
        Computed("buyer IS NOT NULL AND buyer NOT LIKE '%%no Bids%%'", persisted=True),
        nullable=False,
    )
    images_local: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    images_origin: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Auction(id={self.id}, item_no={self.item_no}, name={self.name})>"
