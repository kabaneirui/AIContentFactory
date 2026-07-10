from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import AdapterError, PerformanceSnapshot, PlatformAdapter
from app.integrations.registry import get_adapter_for_account
from app.models import Account, ContentMemory, ContentPerformance, SyncLog, SyncLogStatus
from app.models.content_memory import LifecycleStatus
from app.models.performance_sync_task import PerformanceSyncTask, SyncTaskStatus
from app.services import lifecycle as lifecycle_service


async def apply_performance_snapshot(
    db: AsyncSession,
    video: ContentMemory,
    snapshot: PerformanceSnapshot,
) -> ContentPerformance:
    """Write adapter snapshot into ContentPerformance."""
    result = await db.execute(
        select(ContentPerformance).where(
            ContentPerformance.content_memory_id == video.id
        )
    )
    performance = result.scalar_one_or_none()
    if performance is None:
        performance = ContentPerformance(content_memory_id=video.id)
        db.add(performance)
        video.performance = performance

    performance.views = snapshot.views
    performance.ctr = snapshot.ctr
    performance.rate_3s = snapshot.rate_3s
    performance.finish_rate = snapshot.finish_rate
    performance.average_watch = snapshot.average_watch
    performance.likes = snapshot.likes
    performance.comments = snapshot.comments
    performance.shares = snapshot.shares
    performance.collects = snapshot.collects
    performance.forwards = snapshot.forwards
    performance.fans_increase = snapshot.fans_increase
    performance.reach_level = snapshot.reach_level
    performance.recommend_rate = snapshot.recommend_rate
    performance.engagement_rate = snapshot.engagement_rate
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
    return performance


async def create_sync_log(
    db: AsyncSession,
    *,
    video: ContentMemory,
    adapter_name: str,
    status: SyncLogStatus,
    checkpoint: str | None = None,
    error: str | None = None,
) -> SyncLog:
    log = SyncLog(
        content_memory_id=video.id,
        account_id=video.account_id,
        adapter=adapter_name,
        checkpoint=checkpoint,
        status=status,
        error=error[:4096] if error else None,
        synced_at=datetime.now(UTC),
    )
    db.add(log)
    await db.flush()
    return log


async def sync_video_performance(
    db: AsyncSession,
    video: ContentMemory,
    account: Account,
    *,
    adapter: PlatformAdapter | None = None,
    checkpoint: str | None = None,
) -> SyncLog:
    """Fetch performance via platform adapter and persist results."""
    platform_adapter = adapter or get_adapter_for_account(account, db)
    try:
        snapshot = await platform_adapter.fetch_performance(
            account_id=account.id,
            video_id=video.id,
            platform_video_id=video.platform_video_id,
        )
    except AdapterError as exc:
        return await create_sync_log(
            db,
            video=video,
            adapter_name=platform_adapter.adapter_name,
            status=SyncLogStatus.FAILED,
            checkpoint=checkpoint,
            error=str(exc),
        )
    except Exception as exc:
        return await create_sync_log(
            db,
            video=video,
            adapter_name=platform_adapter.adapter_name,
            status=SyncLogStatus.FAILED,
            checkpoint=checkpoint,
            error=str(exc),
        )

    if snapshot is None:
        return await create_sync_log(
            db,
            video=video,
            adapter_name=platform_adapter.adapter_name,
            status=SyncLogStatus.NO_DATA,
            checkpoint=checkpoint,
        )

    await apply_performance_snapshot(db, video, snapshot)
    return await create_sync_log(
        db,
        video=video,
        adapter_name=platform_adapter.adapter_name,
        status=SyncLogStatus.SUCCESS,
        checkpoint=checkpoint,
    )


async def list_sync_logs_for_video(
    db: AsyncSession,
    video_id: int,
    *,
    account_id: int | None = None,
    limit: int = 50,
) -> list[SyncLog]:
    stmt = (
        select(SyncLog)
        .where(SyncLog.content_memory_id == video_id)
        .order_by(SyncLog.synced_at.desc())
        .limit(limit)
    )
    if account_id is not None:
        stmt = stmt.where(SyncLog.account_id == account_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_account_for_video(db: AsyncSession, video: ContentMemory) -> Account:
    account = await db.get(Account, video.account_id)
    if account is None:
        raise ValueError(f"Account {video.account_id} not found for video {video.id}")
    return account


async def sync_video_by_id(
    db: AsyncSession,
    video_id: int,
    *,
    account_id: int | None = None,
) -> SyncLog:
    stmt = select(ContentMemory).where(ContentMemory.id == video_id)
    if account_id is not None:
        stmt = stmt.where(ContentMemory.account_id == account_id)

    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise ValueError(f"Video {video_id} not found")

    account = await get_account_for_video(db, video)
    return await sync_video_performance(db, video, account)


async def mark_sync_task_completed(
    db: AsyncSession, task: PerformanceSyncTask
) -> PerformanceSyncTask:
    task.status = SyncTaskStatus.COMPLETED
    task.completed_at = datetime.now(UTC)
    await db.flush()
    return task


async def mark_sync_task_failed(
    db: AsyncSession, task: PerformanceSyncTask, error_message: str
) -> PerformanceSyncTask:
    task.status = SyncTaskStatus.FAILED
    task.completed_at = datetime.now(UTC)
    task.error_message = error_message[:1024]
    await db.flush()
    return task
