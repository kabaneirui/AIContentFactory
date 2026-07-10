from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    script: str | None = None
    hook: str | None = Field(default=None, max_length=512)
    template: str | None = Field(default=None, max_length=128)
    knowledge_source: str | None = Field(default=None, max_length=255)
    scene_style: str | None = Field(default=None, max_length=128)
    duration: int | None = Field(default=None, ge=1)
    cta: str | None = Field(default=None, max_length=255)
    dna_tags: dict[str, str] | None = Field(
        default=None,
        description="预估 DNA 标签；未提供时由规则从文案字段推断",
    )


class PredictionResult(BaseModel):
    predict_view: int
    predict_finish_rate: float
    predict_level: int = Field(..., ge=1, le=5)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: list[str]
    threshold: float
    passed: bool


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    video_id: int | None
    title: str
    predict_view: int
    actual_view: int | None
    predict_finish_rate: float
    actual_finish_rate: float | None
    confidence: float
    error_rate: float | None
    predict_level: int
    reason: list[str]
    dna_tags_snapshot: dict[str, Any] | None
    passed: bool
    threshold_used: float
    created_at: datetime
    updated_at: datetime


class PredictApiResponse(BaseModel):
    pass_: bool = Field(alias="pass")
    prediction: PredictionResult
    prediction_id: int

    model_config = ConfigDict(populate_by_name=True)


class PredictionCalibrateRequest(BaseModel):
    video_id: int | None = Field(
        default=None,
        description="发布后关联的视频 ID",
    )
    actual_view: int = Field(..., ge=0)
    actual_finish_rate: float | None = Field(default=None, ge=0.0, le=1.0)
