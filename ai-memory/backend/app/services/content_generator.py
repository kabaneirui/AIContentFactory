"""从决策选题生成完整口播稿。"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account
from app.prompts.content_generation import (
    CONTENT_GENERATION_SYSTEM_PROMPT,
    build_content_generation_user_prompt,
)
from app.schemas.workflow import GenerateScriptRequest, GenerateScriptResponse
from app.services import brain_learner
from app.services.llm_client import OpenAiCompatibleClient, get_llm_client
from app.services.prompt_evolver import DEFAULT_PROMPT_V1, get_active_prompt_version

logger = logging.getLogger(__name__)


class ContentGenerationError(Exception):
    pass


def _profile_summary(profile) -> str:
    if profile is None:
        return "暂无画像，使用通用养生知识类账号风格。"
    parts = [
        f"最佳栏目: {profile.best_category or '—'}",
        f"最佳 Hook: {profile.best_hook or '—'}",
        f"最佳知识源: {profile.best_knowledge_source or '—'}",
        f"最佳画面: {profile.best_scene or '—'}",
        f"最佳时长: {profile.best_duration or '—'}",
        f"最佳 CTA: {profile.best_cta or '—'}",
    ]
    return "\n".join(parts)


def _rule_based_script(payload: GenerateScriptRequest) -> str:
    hook = payload.hook or "你知道吗"
    knowledge = payload.knowledge_source or "养生常识"
    cta = payload.cta or "收藏"
    duration_hint = payload.duration or 32
    trend_line = (
        f"最近{payload.matched_trend}很受关注，"
        if payload.matched_trend
        else ""
    )
    season_line = (
        f"{payload.season or payload.festival}时节，"
        if (payload.season or payload.festival)
        else ""
    )
    return (
        f"{hook}！{season_line}{trend_line}今天跟你分享：{payload.title}。\n\n"
        f"按照{knowledge}的说法，核心就三点：\n"
        f"第一，抓住日常最容易忽略的小习惯；\n"
        f"第二，动作简单，在家就能练；\n"
        f"第三，坚持一周，身体感受会很不一样。\n\n"
        f"（约 {duration_hint} 秒口播量，{payload.template or '口诀'}模板，"
        f"{payload.scene_style or '实拍'}画面）\n\n"
        f"觉得有用记得{cta}，我们下期见。"
    )


async def generate_script(
    db: AsyncSession,
    account: Account,
    payload: GenerateScriptRequest,
    *,
    llm_client: OpenAiCompatibleClient | None = None,
) -> GenerateScriptResponse:
    profile = await brain_learner.get_account_profile(db, account.id)
    active_prompt = await get_active_prompt_version(db, account.id)
    prompt_content = active_prompt.prompt_content if active_prompt else DEFAULT_PROMPT_V1
    prompt_version = active_prompt.version if active_prompt else "V1"

    hook = payload.hook or (profile.best_hook if profile else None) or "老祖宗"
    template = payload.template or (profile.best_category if profile else None) or "口诀"
    knowledge = (
        payload.knowledge_source
        or (profile.best_knowledge_source if profile else None)
        or "黄帝内经"
    )
    scene = payload.scene_style or (profile.best_scene if profile else None) or "古风"
    cta = payload.cta or (profile.best_cta if profile else None) or "收藏"
    duration = payload.duration or 32

    client = llm_client or get_llm_client()
    if client.is_configured:
        system = CONTENT_GENERATION_SYSTEM_PROMPT.format(duration=duration)
        user_prompt = build_content_generation_user_prompt(
            title=payload.title,
            hook=hook,
            template=template,
            knowledge_source=knowledge,
            scene_style=scene,
            duration=duration,
            cta=cta,
            season=payload.season,
            festival=payload.festival,
            matched_trend=payload.matched_trend,
            reasons=payload.reasons,
            prompt_content=prompt_content,
            profile_summary=_profile_summary(profile),
        )
        try:
            raw = await client.complete_json(system=system, user=user_prompt)
            script = raw.get("script")
            title = raw.get("title") or payload.title
            if isinstance(script, str) and script.strip():
                return GenerateScriptResponse(
                    title=str(title).strip(),
                    script=script.strip(),
                    hook=hook,
                    template=template,
                    knowledge_source=knowledge,
                    scene_style=scene,
                    duration=duration,
                    cta=cta,
                    season=payload.season,
                    festival=payload.festival,
                    matched_trend=payload.matched_trend,
                    prompt_version=prompt_version,
                    generated_by="llm",
                )
        except Exception as exc:
            logger.warning(
                "LLM script generation failed for account %s: %s",
                account.id,
                exc,
            )

    normalized = GenerateScriptRequest(
        title=payload.title,
        hook=hook,
        template=template,
        knowledge_source=knowledge,
        scene_style=scene,
        duration=duration,
        cta=cta,
        season=payload.season,
        festival=payload.festival,
        matched_trend=payload.matched_trend,
        reasons=payload.reasons,
    )
    return GenerateScriptResponse(
        title=payload.title,
        script=_rule_based_script(normalized),
        hook=hook,
        template=template,
        knowledge_source=knowledge,
        scene_style=scene,
        duration=duration,
        cta=cta,
        season=payload.season,
        festival=payload.festival,
        matched_trend=payload.matched_trend,
        prompt_version=prompt_version,
        generated_by="rule",
    )
