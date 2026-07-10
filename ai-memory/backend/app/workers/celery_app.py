from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_memory",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.performance_sync_worker",
        "app.workers.dna_tag_worker",
        "app.workers.brain_learning_worker",
        "app.workers.prompt_evolution_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "process-due-performance-syncs": {
        "task": "app.workers.performance_sync_worker.process_due_performance_syncs",
        "schedule": crontab(minute="*/15"),
    },
    "daily-brain-learning": {
        "task": "app.workers.brain_learning_worker.run_daily_brain_learning",
        "schedule": crontab(hour=2, minute=0),
    },
    "daily-prompt-evolution": {
        "task": "app.workers.prompt_evolution_worker.run_prompt_evolution",
        "schedule": crontab(hour=2, minute=30),
    },
}
