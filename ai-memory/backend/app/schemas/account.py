from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(..., min_length=1, max_length=64)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    platform: str | None = Field(default=None, min_length=1, max_length=64)
    predict_threshold: float | None = Field(
        default=None,
        ge=0,
        description="预测拦截阈值（播放量）；为空时使用近 30 条 P25",
    )
    auto_evolve: bool | None = Field(
        default=None,
        description="Prompt 进化后是否自动激活；默认 false 需人工审核",
    )


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: str
    predict_threshold: float | None
    auto_evolve: bool
    created_at: datetime
