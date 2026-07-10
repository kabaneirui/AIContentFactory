from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DimensionRanking(BaseModel):
    name: str
    avg_view: float
    count: int


class HookCtaCombo(BaseModel):
    hook: str
    cta: str
    avg_view: float
    count: int


class LearningStatsSnapshot(BaseModel):
    sample_size: int
    total_eligible: int
    avg_view: float
    template_ranking: list[DimensionRanking] = Field(default_factory=list)
    title_prefix_ranking: list[DimensionRanking] = Field(default_factory=list)
    scene_ranking: list[DimensionRanking] = Field(default_factory=list)
    publish_hour_ranking: list[DimensionRanking] = Field(default_factory=list)
    hook_cta_combos: list[HookCtaCombo] = Field(default_factory=list)
    knowledge_ranking: list[DimensionRanking] = Field(default_factory=list)
    cta_ranking: list[DimensionRanking] = Field(default_factory=list)
    hook_ranking: list[DimensionRanking] = Field(default_factory=list)


class LearningReportContent(BaseModel):
    summary: str
    strength: str
    weakness: str
    trend: str
    suggestion: str
    optimization: str


class BrainLearningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    learning_date: date
    sample_size: int
    summary: str
    strength: str
    weakness: str
    trend: str
    suggestion: str
    optimization: str
    prompt_version: str | None
    stats_snapshot: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
