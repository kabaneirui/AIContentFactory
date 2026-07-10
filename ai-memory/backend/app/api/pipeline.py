from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account
from app.models import Account
from app.schemas.pipeline import PipelinePublishRequest, PipelinePublishResponse
from app.services import content_pipeline
from app.services.dna_trigger import schedule_video_tagging

router = APIRouter(tags=["pipeline"])


@router.post(
    "/accounts/{account_id}/pipeline/publish",
    response_model=PipelinePublishResponse,
    summary="内容生成管线发布钩子",
    description=(
        "供外部内容生成系统调用：写入 Video Memory、调度 T+1h/24h/7d 同步、"
        "触发 Content DNA 打标，并绑定当前活跃 Prompt 版本。"
    ),
)
async def pipeline_publish(
    payload: PipelinePublishRequest,
    background_tasks: BackgroundTasks,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PipelinePublishResponse:
    result = await content_pipeline.run_publish_pipeline(db, account, payload)
    if (
        result.success
        and result.video_id is not None
        and not payload.tag_inline
    ):
        background_tasks.add_task(schedule_video_tagging, result.video_id)
    return result
