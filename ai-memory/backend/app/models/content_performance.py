from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.content_memory import ContentMemory


class ContentPerformance(Base):
    __tablename__ = "content_performances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_memory_id: Mapped[int] = mapped_column(
        ForeignKey("content_memories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_3s: Mapped[float | None] = mapped_column(Float, nullable=True)
    finish_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_watch: Mapped[float | None] = mapped_column(Float, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    comments: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    collects: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    forwards: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    fans_increase: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reach_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recommend_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    content_memory: Mapped["ContentMemory"] = relationship(back_populates="performance")
