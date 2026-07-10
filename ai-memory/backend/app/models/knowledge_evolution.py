import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import AccountScopedMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.content_memory import ContentMemory


class KnowledgeType(str, enum.Enum):
    HIT = "hit"
    FAIL = "fail"


class KnowledgeEvolution(Base, AccountScopedMixin):
    __tablename__ = "knowledge_evolutions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("content_memories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    knowledge_type: Mapped[KnowledgeType] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    analysis_text: Mapped[str] = mapped_column(Text, nullable=False)
    views_at_analysis: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped["Account"] = relationship(back_populates="knowledge_evolutions")
    video: Mapped["ContentMemory"] = relationship(back_populates="knowledge_evolution")
