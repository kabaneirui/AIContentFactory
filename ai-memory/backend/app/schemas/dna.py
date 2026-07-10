from pydantic import BaseModel, ConfigDict, Field


class DnaTags(BaseModel):
    """Content DNA 8 维标签（文档 4.2）。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    title_type: str = Field(..., min_length=1, max_length=128, description="标题类型")
    hook_type: str = Field(..., min_length=1, max_length=128, description="Hook 类型")
    template: str = Field(..., min_length=1, max_length=128, description="内容模板")
    knowledge: str = Field(..., min_length=1, max_length=255, description="知识类型")
    emotion: str = Field(..., min_length=1, max_length=128, description="情绪类型")
    scene: str = Field(..., min_length=1, max_length=128, description="画面类型")
    pacing: str = Field(..., min_length=1, max_length=64, description="镜头节奏")
    cta: str = Field(..., min_length=1, max_length=64, description="CTA 类型")

    def to_storage(self) -> dict[str, str]:
        return self.model_dump()


class BatchTagRequest(BaseModel):
    video_ids: list[int] | None = Field(
        default=None,
        description="指定视频 ID；为空则处理账号下所有未打标视频",
    )
    force: bool = Field(
        default=False,
        description="为 true 时重新打标已有 DNA 标签的视频",
    )


class BatchTagResult(BaseModel):
    queued: int
    video_ids: list[int]


class RetagResponse(BaseModel):
    video_id: int
    dna_tags: dict[str, str]
    lifecycle_status: str
