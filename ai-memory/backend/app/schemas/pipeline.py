from typing import Any

from pydantic import BaseModel, Field

from app.schemas.video import PerformanceUpdate, VideoCreate


class PipelinePublishRequest(VideoCreate):
    """内容生成管线发布钩子：写入 Video Memory 并触发打标与同步调度。"""

    require_prediction_pass: bool = Field(
        default=False,
        description="为 true 时先执行预测，低于阈值则拦截发布",
    )
    tag_inline: bool = Field(
        default=True,
        description="为 true 时同步完成 DNA 打标；false 则异步调度",
    )
    initial_performance: PerformanceUpdate | None = Field(
        default=None,
        description="发布时附带的首批表现数据（可选）",
    )


class PipelineSteps(BaseModel):
    prediction_checked: bool = False
    prediction_passed: bool | None = None
    content_memory_created: bool = False
    sync_tasks_scheduled: int = 0
    dna_tagged: bool = False
    performance_updated: bool = False


class PipelinePublishResponse(BaseModel):
    success: bool
    video_id: int | None = None
    lifecycle_status: str | None = None
    dna_tags: dict[str, Any] | None = None
    sync_tasks_scheduled: int = 0
    prompt_version: str | None = None
    steps: PipelineSteps
    message: str | None = None
