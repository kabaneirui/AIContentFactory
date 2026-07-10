import logging

from app.config import get_settings
from app.services.dna_tagger import tag_video_by_id

logger = logging.getLogger(__name__)


async def run_video_tagging(video_id: int, *, force: bool = False) -> None:
    """在独立会话中执行单条视频 DNA 打标（用于 BackgroundTasks / Celery）。"""
    from app import database

    settings = get_settings()
    if not settings.dna_tagging_enabled:
        return

    async with database.async_session_factory() as session:
        try:
            await tag_video_by_id(session, video_id, force=force)
            await session.commit()
            logger.info("DNA tagging completed for video %s", video_id)
        except Exception:
            await session.rollback()
            logger.exception("DNA tagging failed for video %s", video_id)
            raise


async def schedule_video_tagging(video_id: int, *, force: bool = False) -> None:
    """异步调度 DNA 打标：优先 Celery，否则在当前进程后台执行。"""
    settings = get_settings()
    if not settings.dna_tagging_enabled:
        return

    if settings.dna_tag_use_celery:
        try:
            from app.workers.dna_tag_worker import tag_video_task

            tag_video_task.delay(video_id, force=force)
            return
        except Exception:
            logger.warning(
                "Celery enqueue failed for video %s; falling back to inline task",
                video_id,
                exc_info=True,
            )

    await run_video_tagging(video_id, force=force)


async def schedule_videos_tagging(
    video_ids: list[int], *, force: bool = False
) -> None:
    for video_id in video_ids:
        await schedule_video_tagging(video_id, force=force)
