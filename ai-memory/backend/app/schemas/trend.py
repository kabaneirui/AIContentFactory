from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TrendDirection(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class TrendTopicCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=512)
    category: str | None = Field(default=None, max_length=128)
    heat_score: float = Field(default=50.0, ge=0.0)
    source: str = Field(default="manual", max_length=64)
    trend_date: date | None = None
    season: str | None = Field(default=None, max_length=64)
    festival: str | None = Field(default=None, max_length=128)


class TrendTopicUpdate(BaseModel):
    topic: str | None = Field(default=None, min_length=1, max_length=512)
    category: str | None = Field(default=None, max_length=128)
    heat_score: float | None = Field(default=None, ge=0.0)
    source: str | None = Field(default=None, max_length=64)
    trend_date: date | None = None
    season: str | None = Field(default=None, max_length=64)
    festival: str | None = Field(default=None, max_length=128)


class TrendTopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    category: str | None
    heat_score: float
    source: str
    trend_date: date
    season: str | None
    festival: str | None
    trend_direction: TrendDirection | None = None
    created_at: datetime
    updated_at: datetime


class TrendTopicListResponse(BaseModel):
    items: list[TrendTopicResponse]
    total: int


class TrendImportRow(BaseModel):
    topic: str = Field(..., min_length=1, max_length=512)
    category: str | None = Field(default=None, max_length=128)
    heat_score: float = Field(default=50.0, ge=0.0)
    source: str = Field(default="csv", max_length=64)
    trend_date: date | None = None
    season: str | None = Field(default=None, max_length=64)
    festival: str | None = Field(default=None, max_length=128)


class TrendImportError(BaseModel):
    row: int
    field: str | None = None
    message: str


class TrendImportRequest(BaseModel):
    trends: list[TrendImportRow] = Field(..., min_length=1)


class TrendImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[TrendImportError]
