from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    version: str
    prompt_content: str
    change_log: str | None
    video_count: int
    avg_view: float
    avg_finish_rate: float
    recommend_score: int = Field(..., ge=1, le=5)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PromptVersionListResponse(BaseModel):
    items: list[PromptVersionResponse]
    active_version: str | None


class PromptVersionCreate(BaseModel):
    prompt_content: str = Field(..., min_length=10)
    change_log: str | None = Field(default=None, max_length=2000)
    activate: bool = Field(
        default=False,
        description="创建后是否立即激活；默认需人工审核",
    )


class PromptEvolveRequest(BaseModel):
    force: bool = Field(
        default=False,
        description="忽略触发条件，强制尝试进化",
    )


class PromptEvolveResponse(BaseModel):
    evolved: bool
    reason: str
    new_version: PromptVersionResponse | None = None
    pending_review: bool = False


class PromptCompareResponse(BaseModel):
    version_a: PromptVersionResponse
    version_b: PromptVersionResponse
    view_delta: float
    finish_rate_delta: float
    recommend_delta: int


class PromptActivateResponse(BaseModel):
    activated_version: str
    previous_version: str | None
