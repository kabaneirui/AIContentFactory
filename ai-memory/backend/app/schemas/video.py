from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.content_memory import LifecycleStatus


class VideoCreate(BaseModel):
    platform: str | None = Field(default=None, max_length=64)
    platform_video_id: str | None = Field(default=None, max_length=255)
    title: str = Field(..., min_length=1, max_length=512)
    script: str | None = None
    hook: str | None = Field(default=None, max_length=512)
    template: str | None = Field(default=None, max_length=128)
    knowledge_source: str | None = Field(default=None, max_length=255)
    prompt: str | None = Field(default=None, max_length=128)
    scene_style: str | None = Field(default=None, max_length=128)
    duration: int | None = Field(default=None, ge=0)
    cta: str | None = Field(default=None, max_length=255)
    publish_time: datetime | None = None
    season: str | None = Field(default=None, max_length=64)
    festival: str | None = Field(default=None, max_length=128)
    weather: str | None = Field(default=None, max_length=64)
    keyword: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=128)
    dna_tags: dict[str, Any] | None = None


class VideoImportRow(VideoCreate):
    """Single row for CSV/JSON batch import; title is required per row."""

    views: int | None = Field(default=None, ge=0)
    ctr: float | None = Field(default=None, ge=0)
    rate_3s: float | None = Field(default=None, ge=0, le=1)
    finish_rate: float | None = Field(default=None, ge=0, le=1)
    average_watch: float | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    collects: int | None = Field(default=None, ge=0)
    forwards: int | None = Field(default=None, ge=0)
    fans_increase: int | None = Field(default=None, ge=0)
    reach_level: str | None = Field(default=None, max_length=64)
    recommend_rate: float | None = Field(default=None, ge=0, le=1)
    engagement_rate: float | None = Field(default=None, ge=0, le=1)


class VideoImportRequest(BaseModel):
    videos: list[VideoImportRow] = Field(..., min_length=1)


class VideoImportError(BaseModel):
    row: int
    field: str | None = None
    message: str


class VideoImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[VideoImportError]
    video_ids: list[int] = Field(default_factory=list)


class VideoMetadataUpdate(BaseModel):
    """用于补充/修正视频的平台元数据，如 B站 BV 号。"""

    platform_video_id: str | None = Field(default=None, max_length=255)


class PerformanceUpdate(BaseModel):
    views: int | None = Field(default=None, ge=0)
    ctr: float | None = Field(default=None, ge=0)
    rate_3s: float | None = Field(default=None, ge=0, le=1)
    finish_rate: float | None = Field(default=None, ge=0, le=1)
    average_watch: float | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    collects: int | None = Field(default=None, ge=0)
    forwards: int | None = Field(default=None, ge=0)
    fans_increase: int | None = Field(default=None, ge=0)
    reach_level: str | None = Field(default=None, max_length=64)
    recommend_rate: float | None = Field(default=None, ge=0, le=1)
    engagement_rate: float | None = Field(default=None, ge=0, le=1)


class PerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_memory_id: int
    views: int
    ctr: float | None
    rate_3s: float | None
    finish_rate: float | None
    average_watch: float | None
    likes: int
    comments: int
    shares: int
    collects: int
    forwards: int
    fans_increase: int
    reach_level: str | None
    recommend_rate: float | None
    engagement_rate: float | None
    synced_at: datetime | None
    updated_at: datetime


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    platform: str
    platform_video_id: str | None
    title: str
    script: str | None
    hook: str | None
    template: str | None
    knowledge_source: str | None
    prompt: str | None
    scene_style: str | None
    duration: int | None
    cta: str | None
    publish_time: datetime | None
    season: str | None
    festival: str | None
    weather: str | None
    keyword: str | None
    category: str | None
    dna_tags: dict[str, Any] | None
    lifecycle_status: LifecycleStatus
    created_at: datetime
    updated_at: datetime
    performance: PerformanceResponse | None = None


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int
