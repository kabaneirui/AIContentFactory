from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Memory"
    database_url: str = "postgresql+asyncpg://aimemory:aimemory@localhost:5432/aimemory"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    # Content DNA / LLM（OpenAI 兼容 API）
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 60.0
    dna_tagging_enabled: bool = True
    dna_tag_use_celery: bool = False

    # Platform integrations (Phase 3)
    default_data_adapter: str = "manual"
    wechat_channels_enabled: bool = False
    wechat_channels_app_id: str | None = None
    wechat_channels_app_secret: str | None = None
    wechat_channels_access_token: str | None = None
    wechat_channels_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
