from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmbeddingTask(Base):
    __tablename__ = "embedding_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="pending")
    rebuild: Mapped[bool] = mapped_column(Boolean, default=False)
    limit_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_checkpoint_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
