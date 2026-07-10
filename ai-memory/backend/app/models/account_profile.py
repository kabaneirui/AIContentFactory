from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base

if TYPE_CHECKING:
    from app.models.account import Account


class AccountProfile(Base):
    __tablename__ = "account_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    best_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    best_scene: Mapped[str | None] = mapped_column(String(128), nullable=True)
    best_duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    best_publish_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    best_cta: Mapped[str | None] = mapped_column(String(64), nullable=True)
    best_hook: Mapped[str | None] = mapped_column(String(128), nullable=True)
    best_knowledge_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locked_fields: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped["Account"] = relationship(back_populates="profile")
