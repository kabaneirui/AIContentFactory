from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.sync_log import SyncLogStatus


class SyncLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_memory_id: int
    account_id: int
    adapter: str
    checkpoint: str | None
    status: SyncLogStatus
    error: str | None
    synced_at: datetime


class SyncTriggerResponse(BaseModel):
    video_id: int
    sync_log: SyncLogResponse
    performance_updated: bool


class SyncLogListResponse(BaseModel):
    items: list[SyncLogResponse] = Field(default_factory=list)
    total: int
