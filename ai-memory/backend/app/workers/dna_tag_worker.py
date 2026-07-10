import asyncio
import logging

from app.services.dna_trigger import run_video_tagging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.dna_tag_worker.tag_video_task")
def tag_video_task(video_id: int, force: bool = False) -> dict[str, int | bool]:
    """Celery 任务：为单条视频执行 Content DNA 打标。"""
    asyncio.run(run_video_tagging(video_id, force=force))
    logger.info("Celery DNA tag task finished for video %s", video_id)
    return {"video_id": video_id, "force": force, "success": True}
