from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import AccountScopedMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.content_memory import ContentMemory


class PredictionHistory(Base, AccountScopedMixin):
    __tablename__ = "prediction_histories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_memories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    predict_view: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_view: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predict_finish_rate: Mapped[float] = mapped_column(Float, nullable=False)
    actual_finish_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    predict_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    dna_tags_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    passed: Mapped[bool] = mapped_column(nullable=False)
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped["Account"] = relationship(back_populates="prediction_histories")
    video: Mapped["ContentMemory | None"] = relationship(back_populates="prediction_histories")
