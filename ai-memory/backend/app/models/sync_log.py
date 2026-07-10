import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.content_memory import ContentMemory


class SyncLogStatus(str, enum.Enum):
    SUCCESS = "success"
    NO_DATA = "no_data"
    FAILED = "failed"
    SKIPPED = "skipped"


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_memory_id: Mapped[int] = mapped_column(
        ForeignKey("content_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    adapter: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[SyncLogStatus] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    content_memory: Mapped["ContentMemory"] = relationship(back_populates="sync_logs")
