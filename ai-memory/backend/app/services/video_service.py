from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Account, ContentMemory, ContentPerformance, LifecycleStatus
from app.models.performance_sync_task import (
    PerformanceSyncTask,
    SyncCheckpoint,
    SyncTaskStatus,
)
from app.schemas.video import PerformanceUpdate, VideoCreate, VideoMetadataUpdate
from app.services import lifecycle as lifecycle_service

VideoSortBy = Literal["created_at", "publish_time", "views", "title"]
VideoSortOrder = Literal["asc", "desc"]


CHECKPOINT_DELAYS: dict[SyncCheckpoint, timedelta] = {
    SyncCheckpoint.H1: timedelta(hours=1),
    SyncCheckpoint.H24: timedelta(hours=24),
    SyncCheckpoint.D7: timedelta(days=7),
}


async def create_video(
    db: AsyncSession,
    account: Account,
    payload: VideoCreate,
) -> ContentMemory:
    platform = payload.platform or account.platform
    status = lifecycle_service.initial_status_for_video(
        has_publish_time=payload.publish_time is not None
    )

    video = ContentMemory(
        account_id=account.id,
        platform=platform,
        platform_video_id=payload.platform_video_id,
        title=payload.title,
        script=payload.script,
        hook=payload.hook,
        template=payload.template,
        knowledge_source=payload.knowledge_source,
        prompt=payload.prompt,
        scene_style=payload.scene_style,
        duration=payload.duration,
        cta=payload.cta,
        publish_time=payload.publish_time,
        season=payload.season,
        festival=payload.festival,
        weather=payload.weather,
        keyword=payload.keyword,
        category=payload.category,
        dna_tags=payload.dna_tags,
        lifecycle_status=status,
    )
    db.add(video)
    await db.flush()

    if status == LifecycleStatus.PUBLISHED:
        await schedule_performance_syncs(db, video)

    reloaded = await get_video_by_id(db, video.id)
    assert reloaded is not None
    return reloaded


async def schedule_performance_syncs(
    db: AsyncSession, video: ContentMemory
) -> list[PerformanceSyncTask]:
    """Create T+1h / T+24h / T+7d sync tasks and move lifecycle to syncing."""
    base_time = video.publish_time or datetime.now(UTC)
    tasks: list[PerformanceSyncTask] = []

    for checkpoint, delay in CHECKPOINT_DELAYS.items():
        task = PerformanceSyncTask(
            content_memory_id=video.id,
            checkpoint=checkpoint,
            due_at=base_time + delay,
            status=SyncTaskStatus.PENDING,
        )
        db.add(task)
        tasks.append(task)

    if video.lifecycle_status == LifecycleStatus.PUBLISHED:
        video.lifecycle_status = lifecycle_service.transition(
            video.lifecycle_status, LifecycleStatus.SYNCING
        )

    await db.flush()
    return tasks


async def get_video_by_id(
    db: AsyncSession, video_id: int, *, account_id: int | None = None
) -> ContentMemory | None:
    stmt = (
        select(ContentMemory)
        .options(selectinload(ContentMemory.performance))
        .where(ContentMemory.id == video_id)
    )
    if account_id is not None:
        stmt = stmt.where(ContentMemory.account_id == account_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_videos(
    db: AsyncSession,
    account_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
    lifecycle_status: LifecycleStatus | None = None,
    category: str | None = None,
    template: str | None = None,
    keyword: str | None = None,
    dna_filters: dict[str, str] | None = None,
    sort_by: VideoSortBy = "publish_time",
    sort_order: VideoSortOrder = "desc",
) -> tuple[list[ContentMemory], int]:
    filters = [ContentMemory.account_id == account_id]

    if lifecycle_status is not None:
        filters.append(ContentMemory.lifecycle_status == lifecycle_status)
    if category is not None:
        filters.append(ContentMemory.category == category)
    if template is not None:
        filters.append(ContentMemory.template == template)
    if keyword is not None:
        filters.append(ContentMemory.title.ilike(f"%{keyword}%"))
    if dna_filters:
        filters.extend(_dna_tag_filters(dna_filters))

    count_stmt = select(func.count()).select_from(ContentMemory).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(ContentMemory)
        .options(selectinload(ContentMemory.performance))
        .where(*filters)
    )
    if sort_by == "views":
        stmt = stmt.outerjoin(
            ContentPerformance,
            ContentPerformance.content_memory_id == ContentMemory.id,
        )
        sort_column = func.coalesce(ContentPerformance.views, 0)
        order_expr = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    elif sort_by == "publish_time":
        sort_column = ContentMemory.publish_time
        # 无发布时间的视频一律沉底，避免草稿/未填时间挤在最前。
        order_expr = (
            sort_column.asc().nulls_last()
            if sort_order == "asc"
            else sort_column.desc().nulls_last()
        )
    elif sort_by == "title":
        sort_column = ContentMemory.title
        order_expr = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    else:
        sort_column = ContentMemory.created_at
        order_expr = sort_column.asc() if sort_order == "asc" else sort_column.desc()

    # Stable secondary key so pages don't shuffle on ties.
    stmt = (
        stmt.order_by(order_expr, ContentMemory.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all()), total


async def delete_video(db: AsyncSession, video: ContentMemory) -> None:
    await db.delete(video)
    await db.flush()


async def update_performance(
    db: AsyncSession,
    video: ContentMemory,
    payload: PerformanceUpdate,
) -> ContentPerformance:
    if video.performance is None:
        performance = ContentPerformance(content_memory_id=video.id)
        db.add(performance)
        video.performance = performance
    else:
        performance = video.performance

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(performance, field, value)

    performance.synced_at = datetime.now(UTC)

    if video.lifecycle_status in {
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.SYNCING,
        LifecycleStatus.TAGGED,
    }:
        video.lifecycle_status = lifecycle_service.transition(
            video.lifecycle_status, LifecycleStatus.SYNCING
        )

    await db.flush()
    await db.refresh(performance)
    return performance


async def update_metadata(
    db: AsyncSession,
    video: ContentMemory,
    payload: VideoMetadataUpdate,
) -> ContentMemory:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(video, field, value.strip() if isinstance(value, str) else value)

    await db.flush()
    await db.refresh(video)
    return video


def _dna_tag_filters(dna_filters: dict[str, str]) -> list[Any]:
    clauses: list[Any] = []
    for key, value in dna_filters.items():
        clauses.append(ContentMemory.dna_tags[key].as_string() == value)
    return clauses
