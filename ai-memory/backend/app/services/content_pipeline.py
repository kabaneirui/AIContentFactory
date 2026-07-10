"""内容生成管线钩子：发布 → ContentMemory → DNA 打标 → 表现同步调度。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, PerformanceSyncTask
from app.schemas.pipeline import PipelinePublishRequest, PipelinePublishResponse, PipelineSteps
from app.schemas.prediction import PredictRequest
from app.schemas.video import VideoCreate
from app.services import dna_tagger, predictor, video_service
from app.services.dna_trigger import schedule_video_tagging
from app.services.prompt_evolver import get_active_prompt_version

logger = logging.getLogger(__name__)


async def run_publish_pipeline(
    db: AsyncSession,
    account: Account,
    payload: PipelinePublishRequest,
) -> PipelinePublishResponse:
    """编排发布闭环：可选预测拦截 → 建档 → 同步任务 → DNA 打标。"""
    steps = PipelineSteps()

    if payload.require_prediction_pass:
        predict_payload = PredictRequest(
            title=payload.title,
            script=payload.script,
            hook=payload.hook,
            template=payload.template,
            knowledge_source=payload.knowledge_source,
            scene_style=payload.scene_style,
            duration=payload.duration,
            cta=payload.cta,
            dna_tags=payload.dna_tags,
        )
        _, result = await predictor.create_prediction(db, account, predict_payload)
        steps.prediction_checked = True
        steps.prediction_passed = result.passed
        if not result.passed:
            return PipelinePublishResponse(
                success=False,
                steps=steps,
                message="预测播放低于账号阈值，发布已拦截",
            )

    prompt_version = payload.prompt
    if prompt_version is None:
        active = await get_active_prompt_version(db, account.id)
        if active is not None:
            prompt_version = active.version

    publish_time = payload.publish_time or datetime.now(UTC)
    video_payload = VideoCreate(
        platform=payload.platform,
        platform_video_id=payload.platform_video_id,
        title=payload.title,
        script=payload.script,
        hook=payload.hook,
        template=payload.template,
        knowledge_source=payload.knowledge_source,
        prompt=prompt_version,
        scene_style=payload.scene_style,
        duration=payload.duration,
        cta=payload.cta,
        publish_time=publish_time,
        season=payload.season,
        festival=payload.festival,
        weather=payload.weather,
        keyword=payload.keyword,
        category=payload.category,
        dna_tags=payload.dna_tags,
    )

    video = await video_service.create_video(db, account, video_payload)
    steps.content_memory_created = True

    if payload.initial_performance is not None:
        await video_service.update_performance(db, video, payload.initial_performance)
        steps.performance_updated = True

    sync_result = await db.execute(
        select(PerformanceSyncTask).where(
            PerformanceSyncTask.content_memory_id == video.id
        )
    )
    sync_tasks = list(sync_result.scalars().all())
    steps.sync_tasks_scheduled = len(sync_tasks)

    if payload.tag_inline:
        tags = await dna_tagger.tag_video(db, video, force=False)
        steps.dna_tagged = True
        dna_tags = tags.to_storage()
    else:
        await schedule_video_tagging(video.id)
        steps.dna_tagged = False
        dna_tags = video.dna_tags

    await db.refresh(video)
    lifecycle = (
        video.lifecycle_status.value
        if hasattr(video.lifecycle_status, "value")
        else str(video.lifecycle_status)
    )

    logger.info(
        "Publish pipeline completed for account %s video %s (inline_tag=%s)",
        account.id,
        video.id,
        payload.tag_inline,
    )

    return PipelinePublishResponse(
        success=True,
        video_id=video.id,
        lifecycle_status=lifecycle,
        dna_tags=dna_tags or video.dna_tags,
        sync_tasks_scheduled=steps.sync_tasks_scheduled,
        prompt_version=prompt_version,
        steps=steps,
    )
