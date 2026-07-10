import asyncio
import logging

from app.database import async_session_factory
from app.services.brain_learner import run_daily_learning_for_all_accounts
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_daily_learning() -> dict[str, int]:
    async with async_session_factory() as session:
        try:
            result = await run_daily_learning_for_all_accounts(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


@celery_app.task(name="app.workers.brain_learning_worker.run_daily_brain_learning")
def run_daily_brain_learning() -> dict[str, int]:
    """Celery beat task: daily Brain Learning at 02:00 Asia/Shanghai."""
    result = asyncio.run(_run_daily_learning())
    logger.info("Daily brain learning complete: %s", result)
    return result
