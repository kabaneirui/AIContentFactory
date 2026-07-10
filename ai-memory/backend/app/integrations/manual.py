"""Manual import adapter — reads performance already stored in the database."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.base import PerformanceSnapshot, PlatformAdapter, PlatformVideoItem
from app.models.content_memory import ContentMemory


class ManualAdapter(PlatformAdapter):
    """P0 adapter: performance is entered via PATCH API or CSV import."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def adapter_name(self) -> str:
        return "manual"

    async def fetch_performance(
        self,
        *,
        account_id: int,
        video_id: int,
        platform_video_id: str | None,
    ) -> PerformanceSnapshot | None:
        video = await self._load_video(account_id=account_id, video_id=video_id)
        if video is None or video.performance is None:
            return None
        return _snapshot_from_performance(video.performance)

    async def list_videos(
        self,
        *,
        account_id: int,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformVideoItem]:
        stmt = (
            select(ContentMemory)
            .options(selectinload(ContentMemory.performance))
            .where(ContentMemory.account_id == account_id)
            .order_by(ContentMemory.created_at.desc())
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(ContentMemory.publish_time >= since)

        result = await self._db.execute(stmt)
        items: list[PlatformVideoItem] = []
        for video in result.scalars().all():
            if not video.platform_video_id:
                continue
            perf = (
                _snapshot_from_performance(video.performance)
                if video.performance is not None
                else None
            )
            items.append(
                PlatformVideoItem(
                    platform_video_id=video.platform_video_id,
                    title=video.title,
                    publish_time=video.publish_time,
                    performance=perf,
                )
            )
        return items

    async def _load_video(
        self, *, account_id: int, video_id: int
    ) -> ContentMemory | None:
        stmt = (
            select(ContentMemory)
            .options(selectinload(ContentMemory.performance))
            .where(
                ContentMemory.id == video_id,
                ContentMemory.account_id == account_id,
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()


def _snapshot_from_performance(performance) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        views=performance.views,
        ctr=performance.ctr,
        rate_3s=performance.rate_3s,
        finish_rate=performance.finish_rate,
        average_watch=performance.average_watch,
        likes=performance.likes,
        comments=performance.comments,
        shares=performance.shares,
        collects=performance.collects,
        forwards=performance.forwards,
        fans_increase=performance.fans_increase,
        reach_level=performance.reach_level,
        recommend_rate=performance.recommend_rate,
        engagement_rate=performance.engagement_rate,
    )
