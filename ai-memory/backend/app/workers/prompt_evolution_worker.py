import asyncio
import logging

from app.database import async_session_factory
from app.services.prompt_evolver import run_prompt_evolution_for_all_accounts
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_prompt_evolution() -> dict[str, int]:
    async with async_session_factory() as session:
        try:
            result = await run_prompt_evolution_for_all_accounts(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


@celery_app.task(name="app.workers.prompt_evolution_worker.run_prompt_evolution")
def run_prompt_evolution() -> dict[str, int]:
    """Celery beat task: check prompt evolution after daily learning."""
    result = asyncio.run(_run_prompt_evolution())
    logger.info("Prompt evolution check complete: %s", result)
    return result
