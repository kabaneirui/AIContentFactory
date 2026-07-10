from datetime import datetime

from pydantic import BaseModel, Field


class DecideTodayRequest(BaseModel):
    season: str | None = Field(
        default=None,
        max_length=64,
        description="当前节气，用于热点与选题时效匹配",
    )
    festival: str | None = Field(
        default=None,
        max_length=128,
        description="当前节日，用于热点与选题时效匹配",
    )
    platform: str | None = Field(
        default=None,
        max_length=64,
        description="发布平台；默认使用账号平台",
    )
    count: int = Field(
        default=5,
        ge=3,
        le=5,
        description="推荐候选数量（3-5）",
    )


class DecisionRecommendation(BaseModel):
    rank: int
    title: str
    predict_level: int = Field(..., ge=1, le=5)
    predict_view: int = Field(..., ge=0)
    suggested_publish_time: str
    reasons: list[str]
    account_weight_score: float = Field(..., ge=0.0, le=1.0)
    trend_weight_score: float = Field(..., ge=0.0, le=1.0)
    combined_score: float = Field(..., ge=0.0, le=1.0)
    matched_trend: str | None = None
    template: str | None = None
    hook: str | None = None
    knowledge_source: str | None = None
    scene_style: str | None = None
    duration: int | None = None
    cta: str | None = None


class DecideTodayResponse(BaseModel):
    account_id: int
    generated_at: datetime
    season: str | None
    festival: str | None
    platform: str | None
    recommendations: list[DecisionRecommendation]
