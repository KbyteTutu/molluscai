import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )
    daily_query_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    query_logs: Mapped[List["QueryLog"]] = relationship(
        "QueryLog", back_populates="user", lazy="selectin"
    )
    billing_records: Mapped[List["BillingRecord"]] = relationship(
        "BillingRecord", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class RoleQuota(Base):
    __tablename__ = "role_quotas"

    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    daily_auction_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_rag_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<RoleQuota(role={self.role})>"


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    result_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0.0000")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="query_logs")

    def __repr__(self) -> str:
        return f"<QueryLog(id={self.id}, user_id={self.user_id}, query_type={self.query_type})>"
