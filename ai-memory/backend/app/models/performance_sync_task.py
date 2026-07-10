import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.content_memory import ContentMemory


class SyncCheckpoint(str, enum.Enum):
    H1 = "1h"
    H24 = "24h"
    D7 = "7d"


class SyncTaskStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PerformanceSyncTask(Base):
    __tablename__ = "performance_sync_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_memory_id: Mapped[int] = mapped_column(
        ForeignKey("content_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkpoint: Mapped[SyncCheckpoint] = mapped_column(String(8), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SyncTaskStatus] = mapped_column(
        String(16),
        nullable=False,
        default=SyncTaskStatus.PENDING,
        server_default=SyncTaskStatus.PENDING.value,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    content_memory: Mapped["ContentMemory"] = relationship(back_populates="sync_tasks")
