import logging
import re

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentMemory, LifecycleStatus
from app.prompts.dna_tagging import (
    DNA_TAGGING_SYSTEM_PROMPT,
    build_dna_tagging_user_prompt,
)
from app.schemas.dna import DnaTags
from app.services import lifecycle as lifecycle_service
from app.services.llm_client import OpenAiCompatibleClient, get_llm_client

logger = logging.getLogger(__name__)

DNA_TAGGABLE_STATUSES = {
    LifecycleStatus.CREATED,
    LifecycleStatus.PUBLISHED,
    LifecycleStatus.SYNCING,
    LifecycleStatus.TAGGED,
}


class DnaTaggingError(Exception):
    pass


async def generate_dna_tags(
    video: ContentMemory,
    *,
    llm_client: OpenAiCompatibleClient | None = None,
) -> DnaTags:
    client = llm_client or get_llm_client()
    if client.is_configured:
        return await _generate_with_llm(video, client)
    logger.info(
        "LLM not configured; using rule-based DNA tags for video %s", video.id
    )
    return _generate_rule_based(video)


async def _generate_with_llm(
    video: ContentMemory, client: OpenAiCompatibleClient
) -> DnaTags:
    user_prompt = build_dna_tagging_user_prompt(
        title=video.title,
        script=video.script,
        hook=video.hook,
        template=video.template,
        knowledge_source=video.knowledge_source,
        scene_style=video.scene_style,
        cta=video.cta,
        category=video.category,
        keyword=video.keyword,
        duration=video.duration,
    )
    try:
        raw = await client.complete_json(
            system=DNA_TAGGING_SYSTEM_PROMPT,
            user=user_prompt,
        )
        return DnaTags.model_validate(raw)
    except (ValidationError, ValueError, KeyError) as exc:
        raise DnaTaggingError(f"Invalid LLM DNA tag output: {exc}") from exc
    except Exception as exc:
        raise DnaTaggingError(f"LLM DNA tagging failed: {exc}") from exc


def _generate_rule_based(video: ContentMemory) -> DnaTags:
    title = video.title or ""
    hook = video.hook or ""

    title_type = _infer_title_type(title)
    hook_type = hook or _infer_hook_type(title)
    template = video.template or _infer_template(title, video.script)
    knowledge = video.knowledge_source or _infer_knowledge(title, video.script)
    emotion = _infer_emotion(title, video.script)
    scene = video.scene_style or _infer_scene(video.template, title)
    pacing = _infer_pacing(video.duration)
    cta = video.cta or _infer_cta(video.script)

    return DnaTags(
        title_type=title_type,
        hook_type=hook_type,
        template=template,
        knowledge=knowledge,
        emotion=emotion,
        scene=scene,
        pacing=pacing,
        cta=cta,
    )


def _infer_title_type(title: str) -> str:
    if "口诀" in title:
        return "口诀型"
    if re.search(r"\d", title):
        return "数字型"
    if any(marker in title for marker in ("?", "？", "吗", "怎么", "为什么")):
        return "疑问型"
    return "陈述型"


def _infer_hook_type(title: str) -> str:
    for candidate in ("老祖宗", "很多人", "60岁以后", "你知道吗"):
        if candidate in title:
            return candidate
    return "通用开场"


def _infer_template(title: str, script: str | None) -> str:
    text = f"{title} {script or ''}"
    for candidate in ("口诀", "动作", "情绪", "科普"):
        if candidate in text:
            return candidate
    return "通用"


def _infer_knowledge(title: str, script: str | None) -> str:
    text = f"{title} {script or ''}"
    for candidate in ("黄帝内经", "养阳", "养心", "经络", "脾胃"):
        if candidate in text:
            return candidate
    return "养生常识"


def _infer_emotion(title: str, script: str | None) -> str:
    text = f"{title} {script or ''}"
    if any(word in text for word in ("焦虑", "担心", "害怕")):
        return "焦虑感"
    if any(word in text for word in ("共鸣", "是不是你", "你也")):
        return "共鸣感"
    if any(word in text for word in ("你知道吗", "原来", "竟然")):
        return "好奇感"
    return "获得感"


def _infer_scene(template: str | None, title: str) -> str:
    if template == "口诀" or "古风" in title or "老祖宗" in title:
        return "古风"
    if template == "动作":
        return "实拍"
    return "数字人"


def _infer_pacing(duration: int | None) -> str:
    if duration is None:
        return "混合"
    if duration <= 30:
        return "快切"
    if duration >= 90:
        return "慢节奏"
    return "混合"


def _infer_cta(script: str | None) -> str:
    text = script or ""
    for candidate in ("收藏", "关注", "评论", "转发"):
        if candidate in text:
            return candidate
    return "收藏"


def _apply_lifecycle_after_tagging(video: ContentMemory) -> None:
    if video.lifecycle_status in {
        LifecycleStatus.SYNCING,
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.CREATED,
        LifecycleStatus.TAGGED,
    }:
        video.lifecycle_status = lifecycle_service.transition(
            video.lifecycle_status, LifecycleStatus.TAGGED
        )


async def tag_video(
    db: AsyncSession,
    video: ContentMemory,
    *,
    force: bool = False,
    llm_client: OpenAiCompatibleClient | None = None,
) -> DnaTags:
    if video.lifecycle_status not in DNA_TAGGABLE_STATUSES:
        raise DnaTaggingError(
            f"Video {video.id} lifecycle '{video.lifecycle_status.value}' "
            "cannot be tagged"
        )
    if video.dna_tags and not force:
        return DnaTags.model_validate(video.dna_tags)

    tags = await generate_dna_tags(video, llm_client=llm_client)
    video.dna_tags = tags.to_storage()
    _apply_lifecycle_after_tagging(video)
    await db.flush()
    return tags


async def tag_video_by_id(
    db: AsyncSession,
    video_id: int,
    *,
    account_id: int | None = None,
    force: bool = False,
    llm_client: OpenAiCompatibleClient | None = None,
) -> DnaTags:
    stmt = select(ContentMemory).where(ContentMemory.id == video_id)
    if account_id is not None:
        stmt = stmt.where(ContentMemory.account_id == account_id)

    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise DnaTaggingError(f"Video {video_id} not found")

    return await tag_video(db, video, force=force, llm_client=llm_client)


async def list_videos_for_batch_tag(
    db: AsyncSession,
    account_id: int,
    *,
    video_ids: list[int] | None = None,
    force: bool = False,
) -> list[int]:
    filters = [
        ContentMemory.account_id == account_id,
        ContentMemory.lifecycle_status.in_(DNA_TAGGABLE_STATUSES),
    ]
    if video_ids:
        filters.append(ContentMemory.id.in_(video_ids))
    elif not force:
        filters.append(ContentMemory.dna_tags.is_(None))

    stmt = select(ContentMemory.id).where(*filters).order_by(ContentMemory.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
