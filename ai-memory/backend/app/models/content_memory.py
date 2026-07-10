import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import AccountScopedMixin

if TYPE_CHECKING:
    from app.models.content_performance import ContentPerformance
    from app.models.knowledge_evolution import KnowledgeEvolution
    from app.models.performance_sync_task import PerformanceSyncTask
    from app.models.prediction_history import PredictionHistory
    from app.models.sync_log import SyncLog


class LifecycleStatus(str, enum.Enum):
    CREATED = "created"
    PUBLISHED = "published"
    SYNCING = "syncing"
    TAGGED = "tagged"
    LEARNED = "learned"
    ARCHIVED = "archived"


class ContentMemory(Base, AccountScopedMixin):
    __tablename__ = "content_memories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    script: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook: Mapped[str | None] = mapped_column(String(512), nullable=True)
    template: Mapped[str | None] = mapped_column(String(128), nullable=True)
    knowledge_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scene_style: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    season: Mapped[str | None] = mapped_column(String(64), nullable=True)
    festival: Mapped[str | None] = mapped_column(String(128), nullable=True)
    weather: Mapped[str | None] = mapped_column(String(64), nullable=True)
    keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dna_tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        String(32),
        nullable=False,
        default=LifecycleStatus.CREATED,
        server_default=LifecycleStatus.CREATED.value,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    performance: Mapped["ContentPerformance | None"] = relationship(
        back_populates="content_memory",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sync_tasks: Mapped[list["PerformanceSyncTask"]] = relationship(
        back_populates="content_memory",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(
        back_populates="content_memory",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    prediction_histories: Mapped[list["PredictionHistory"]] = relationship(
        back_populates="video",
        lazy="selectin",
    )
    knowledge_evolution: Mapped["KnowledgeEvolution | None"] = relationship(
        back_populates="video",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
