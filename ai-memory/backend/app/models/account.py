from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.account_profile import AccountProfile
    from app.models.brain_learning import BrainLearning
    from app.models.knowledge_evolution import KnowledgeEvolution
    from app.models.prediction_history import PredictionHistory
    from app.models.prompt_version import PromptVersion


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    predict_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    auto_evolve: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    brain_learnings: Mapped[list["BrainLearning"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    profile: Mapped["AccountProfile | None"] = relationship(
        back_populates="account",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    prediction_histories: Mapped[list["PredictionHistory"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    knowledge_evolutions: Mapped[list["KnowledgeEvolution"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    prompt_versions: Mapped[list["PromptVersion"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
