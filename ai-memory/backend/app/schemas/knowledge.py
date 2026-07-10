from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DimensionScore(BaseModel):
    score: int = Field(..., ge=1, le=5)
    note: str


class KnowledgeEvolutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    video_id: int
    knowledge_type: str
    dimension_scores: dict[str, Any]
    analysis_text: str
    views_at_analysis: int
    created_at: datetime
    updated_at: datetime


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeEvolutionResponse]
    total: int


class StrategyOptimization(BaseModel):
    failure_reasons: list[str]
    increase: list[str]
    decrease: list[str]
    optimize: list[str]
    summary: str
