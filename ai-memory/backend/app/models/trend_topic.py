from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrendTopic(Base):
    """全网热点话题（非账号级，供决策中心 30% 权重输入）。"""

    __tablename__ = "trend_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    heat_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    trend_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    season: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    festival: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
