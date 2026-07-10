from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    platform: str | None
    account_type: str | None
    best_category: str | None
    best_scene: str | None
    best_duration: str | None
    best_publish_time: str | None
    best_cta: str | None
    best_hook: str | None
    best_knowledge_source: str | None
    locked_fields: list[str] | None
    updated_at: datetime


class AccountProfileUpdate(BaseModel):
    locked_fields: list[str] | None = Field(
        default=None,
        description="锁定字段名列表，刷新画像时不会被覆盖",
    )
