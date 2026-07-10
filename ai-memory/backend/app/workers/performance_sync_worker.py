import asyncio
import logging

from app.database import async_session_factory
from app.services.performance_sync_service import process_due_sync_tasks
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_sync_processor() -> dict[str, int]:
    async with async_session_factory() as session:
        try:
            result = await process_due_sync_tasks(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


@celery_app.task(name="app.workers.performance_sync_worker.process_due_performance_syncs")
def process_due_performance_syncs() -> dict[str, int]:
    """Celery beat task: sync T+1h / T+24h / T+7d performance via platform adapters."""
    result = asyncio.run(_run_sync_processor())
    logger.info("Performance sync batch complete: %s", result)
    return result
