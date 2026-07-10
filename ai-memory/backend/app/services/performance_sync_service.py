from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Account, ContentMemory, SyncLogStatus
from app.models.performance_sync_task import PerformanceSyncTask, SyncTaskStatus
from app.services.performance_apply_service import (
    create_sync_log,
    get_account_for_video,
    mark_sync_task_completed,
    mark_sync_task_failed,
    sync_video_performance,
)


async def list_due_sync_tasks(
    db: AsyncSession, *, as_of: datetime | None = None
) -> list[PerformanceSyncTask]:
    """Return pending sync tasks that are due for processing."""
    now = as_of or datetime.now(UTC)
    stmt = (
        select(PerformanceSyncTask)
        .options(
            selectinload(PerformanceSyncTask.content_memory).selectinload(
                ContentMemory.performance
            )
        )
        .where(
            PerformanceSyncTask.status == SyncTaskStatus.PENDING,
            PerformanceSyncTask.due_at <= now,
        )
        .order_by(PerformanceSyncTask.due_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def process_due_sync_tasks(db: AsyncSession) -> dict[str, int]:
    """Process due T+1h / T+24h / T+7d tasks via platform adapters."""
    tasks = await list_due_sync_tasks(db)
    processed = 0
    failed = 0
    no_data = 0

    account_cache: dict[int, Account] = {}

    for task in tasks:
        video = task.content_memory
        if video is None:
            await mark_sync_task_failed(db, task, "content_memory missing")
            failed += 1
            continue

        if video.account_id not in account_cache:
            account_cache[video.account_id] = await get_account_for_video(db, video)
        account = account_cache[video.account_id]

        checkpoint = (
            task.checkpoint.value
            if hasattr(task.checkpoint, "value")
            else str(task.checkpoint)
        )

        try:
            sync_log = await sync_video_performance(
                db,
                video,
                account,
                checkpoint=checkpoint,
            )
            if sync_log.status == SyncLogStatus.FAILED:
                await mark_sync_task_failed(db, task, sync_log.error or "sync failed")
                failed += 1
            else:
                await mark_sync_task_completed(db, task)
                processed += 1
                if sync_log.status == SyncLogStatus.NO_DATA:
                    no_data += 1
        except Exception as exc:
            await mark_sync_task_failed(db, task, str(exc))
            await create_sync_log(
                db,
                video=video,
                adapter_name="unknown",
                status=SyncLogStatus.FAILED,
                checkpoint=checkpoint,
                error=str(exc),
            )
            failed += 1

    return {
        "processed": processed,
        "failed": failed,
        "no_data": no_data,
        "total_due": len(tasks),
    }
