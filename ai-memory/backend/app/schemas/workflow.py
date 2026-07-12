from pydantic import BaseModel, Field


class GenerateScriptRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    hook: str | None = Field(default=None, max_length=512)
    template: str | None = Field(default=None, max_length=128)
    knowledge_source: str | None = Field(default=None, max_length=255)
    scene_style: str | None = Field(default=None, max_length=128)
    duration: int | None = Field(default=None, ge=1)
    cta: str | None = Field(default=None, max_length=255)
    season: str | None = Field(default=None, max_length=64)
    festival: str | None = Field(default=None, max_length=128)
    matched_trend: str | None = Field(default=None, max_length=255)
    reasons: list[str] = Field(default_factory=list)


class GenerateScriptResponse(BaseModel):
    title: str
    script: str
    hook: str | None = None
    template: str | None = None
    knowledge_source: str | None = None
    scene_style: str | None = None
    duration: int | None = None
    cta: str | None = None
    season: str | None = None
    festival: str | None = None
    matched_trend: str | None = None
    prompt_version: str | None = None
    generated_by: str = Field(description="llm | rule")
