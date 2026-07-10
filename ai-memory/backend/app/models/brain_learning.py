from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import AccountScopedMixin

if TYPE_CHECKING:
    from app.models.account import Account


class BrainLearning(Base, AccountScopedMixin):
    __tablename__ = "brain_learnings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    learning_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    strength: Mapped[str] = mapped_column(Text, nullable=False)
    weakness: Mapped[str] = mapped_column(Text, nullable=False)
    trend: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    optimization: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stats_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped["Account"] = relationship(back_populates="brain_learnings")
