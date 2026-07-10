"""Knowledge Evolution：爆款/失败判定与 5 维归因分析。"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Account,
    AccountProfile,
    ContentMemory,
    KnowledgeEvolution,
    KnowledgeType,
    LifecycleStatus,
)
from app.prompts.knowledge_analysis import (
    KNOWLEDGE_ANALYSIS_SYSTEM_PROMPT,
    build_knowledge_analysis_user_prompt,
)
from app.schemas.knowledge import DimensionScore
from app.services import brain_learner, predictor
from app.services.llm_client import OpenAiCompatibleClient, get_llm_client

logger = logging.getLogger(__name__)

KNOWLEDGE_ELIGIBLE_STATUSES = {
    LifecycleStatus.TAGGED,
    LifecycleStatus.LEARNED,
    LifecycleStatus.SYNCING,
    LifecycleStatus.PUBLISHED,
}

DIMENSION_KEYS = ("title", "hook", "knowledge", "collect_value", "engagement")


class KnowledgeAnalyzerError(Exception):
    pass


def classify_video(
    views: int,
    *,
    p25: float,
    p75: float,
) -> KnowledgeType | None:
    if views >= p75:
        return KnowledgeType.HIT
    if views <= p25:
        return KnowledgeType.FAIL
    return None


def _dna_value(video: ContentMemory, key: str) -> str | None:
    if not video.dna_tags:
        return None
    value = video.dna_tags.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _score_dimension(
    actual: str | None,
    best: str | None,
    *,
    knowledge_type: KnowledgeType,
    label: str,
) -> DimensionScore:
    if not actual:
        score = 2 if knowledge_type == KnowledgeType.FAIL else 3
        return DimensionScore(score=score, note=f"{label}信息缺失")

    if best and actual == best:
        score = 5 if knowledge_type == KnowledgeType.HIT else 2
        note = f"{label}「{actual}」符合账号最佳"
    elif best:
        score = 4 if knowledge_type == KnowledgeType.HIT else 2
        note = f"{label}「{actual}」与账号最佳「{best}」有差距"
    else:
        score = 4 if knowledge_type == KnowledgeType.HIT else 3
        note = f"{label}「{actual}」表现{'突出' if knowledge_type == KnowledgeType.HIT else '一般'}"

    return DimensionScore(score=score, note=note)


def _build_rule_dimension_scores(
    video: ContentMemory,
    profile: AccountProfile | None,
    *,
    knowledge_type: KnowledgeType,
    views: int,
    avg_view: float,
) -> dict[str, dict[str, str | int]]:
    title_type = _dna_value(video, "title_type") or video.template or "标题"
    hook = _dna_value(video, "hook_type") or video.hook
    knowledge = _dna_value(video, "knowledge") or video.knowledge_source
    cta = _dna_value(video, "cta") or video.cta

    scores = {
        "title": _score_dimension(
            title_type,
            profile.best_category if profile else None,
            knowledge_type=knowledge_type,
            label="标题类型",
        ),
        "hook": _score_dimension(
            hook,
            profile.best_hook if profile else None,
            knowledge_type=knowledge_type,
            label="Hook",
        ),
        "knowledge": _score_dimension(
            knowledge,
            profile.best_knowledge_source if profile else None,
            knowledge_type=knowledge_type,
            label="知识",
        ),
        "collect_value": _score_dimension(
            cta,
            profile.best_cta if profile else None,
            knowledge_type=knowledge_type,
            label="收藏价值/CTA",
        ),
    }

    finish = video.performance.finish_rate if video.performance else None
    if finish is not None and finish >= 0.3:
        engagement = DimensionScore(score=4, note=f"完播率 {finish:.1%}，互动正常")
    elif finish is not None:
        engagement = DimensionScore(score=2, note=f"完播率 {finish:.1%}，互动偏弱")
    else:
        engagement = DimensionScore(score=3, note="互动数据待同步")

    scores["engagement"] = engagement
    return {key: value.model_dump() for key, value in scores.items()}


def _build_rule_analysis_text(
    video: ContentMemory,
    *,
    knowledge_type: KnowledgeType,
    views: int,
    avg_view: float,
) -> str:
    label = "爆款" if knowledge_type == KnowledgeType.HIT else "失败"
    ratio = views / avg_view if avg_view > 0 else 0
    return (
        f"该视频为账号近期{label}样本，播放 {views}（约为均值的 {ratio:.0%}）。"
        f"标题「{video.title}」在模板与 Hook 维度可作为"
        f"{'正向' if knowledge_type == KnowledgeType.HIT else '负向'}参考样本。"
    )


async def _generate_analysis(
    account: Account,
    video: ContentMemory,
    profile: AccountProfile | None,
    *,
    knowledge_type: KnowledgeType,
    views: int,
    avg_view: float,
    llm_client: OpenAiCompatibleClient | None = None,
) -> tuple[dict[str, dict[str, str | int]], str]:
    rule_scores = _build_rule_dimension_scores(
        video,
        profile,
        knowledge_type=knowledge_type,
        views=views,
        avg_view=avg_view,
    )
    rule_text = _build_rule_analysis_text(
        video,
        knowledge_type=knowledge_type,
        views=views,
        avg_view=avg_view,
    )

    client = llm_client or get_llm_client()
    if not client.is_configured:
        return rule_scores, rule_text

    dna_json = json.dumps(video.dna_tags or {}, ensure_ascii=False)
    profile_json = json.dumps(
        {
            "best_category": profile.best_category if profile else None,
            "best_hook": profile.best_hook if profile else None,
            "best_knowledge_source": (
                profile.best_knowledge_source if profile else None
            ),
        },
        ensure_ascii=False,
    )
    user_prompt = build_knowledge_analysis_user_prompt(
        knowledge_type=knowledge_type.value,
        title=video.title,
        views=views,
        avg_view=avg_view,
        dna_tags_json=dna_json,
        profile_json=profile_json,
    )
    try:
        raw = await client.complete_json(
            system=KNOWLEDGE_ANALYSIS_SYSTEM_PROMPT,
            user=user_prompt,
        )
        dimension_scores = raw.get("dimension_scores")
        analysis_text = raw.get("analysis_text")
        if isinstance(dimension_scores, dict) and isinstance(analysis_text, str):
            validated: dict[str, dict[str, str | int]] = {}
            for key in DIMENSION_KEYS:
                item = dimension_scores.get(key, rule_scores.get(key))
                if isinstance(item, dict):
                    validated[key] = DimensionScore.model_validate(item).model_dump()
                else:
                    validated[key] = rule_scores[key]
            return validated, analysis_text
    except (ValidationError, ValueError, KeyError, Exception) as exc:
        logger.warning(
            "LLM knowledge analysis failed for video %s: %s",
            video.id,
            exc,
        )

    return rule_scores, rule_text


async def analyze_video(
    db: AsyncSession,
    account: Account,
    video: ContentMemory,
    knowledge_type: KnowledgeType,
    *,
    avg_view: float,
    llm_client: OpenAiCompatibleClient | None = None,
) -> KnowledgeEvolution:
    profile = await brain_learner.get_account_profile(db, account.id)
    views = video.performance.views if video.performance else 0
    dimension_scores, analysis_text = await _generate_analysis(
        account,
        video,
        profile,
        knowledge_type=knowledge_type,
        views=views,
        avg_view=avg_view,
        llm_client=llm_client,
    )

    existing = await db.execute(
        select(KnowledgeEvolution).where(KnowledgeEvolution.video_id == video.id)
    )
    record = existing.scalar_one_or_none()
    if record is None:
        record = KnowledgeEvolution(
            account_id=account.id,
            video_id=video.id,
        )
        db.add(record)

    record.knowledge_type = knowledge_type
    record.dimension_scores = dimension_scores
    record.analysis_text = analysis_text
    record.views_at_analysis = views
    await db.flush()
    return record


async def list_knowledge(
    db: AsyncSession,
    account_id: int,
    *,
    knowledge_type: KnowledgeType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[KnowledgeEvolution], int]:
    filters = [KnowledgeEvolution.account_id == account_id]
    if knowledge_type is not None:
        filters.append(KnowledgeEvolution.knowledge_type == knowledge_type)

    count_stmt = select(func.count()).select_from(KnowledgeEvolution).where(*filters)
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        select(KnowledgeEvolution)
        .where(*filters)
        .order_by(KnowledgeEvolution.created_at.desc(), KnowledgeEvolution.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def run_knowledge_evolution_for_account(
    db: AsyncSession,
    account_id: int,
    *,
    llm_client: OpenAiCompatibleClient | None = None,
) -> dict[str, int]:
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if account is None:
        raise KnowledgeAnalyzerError(f"Account {account_id} not found")

    benchmarks = await predictor.compute_view_benchmarks(db, account_id)
    if benchmarks.sample_count < 4:
        return {"hits": 0, "fails": 0, "skipped": 0}

    stmt = (
        select(ContentMemory)
        .options(selectinload(ContentMemory.performance))
        .where(
            ContentMemory.account_id == account_id,
            ContentMemory.dna_tags.is_not(None),
            ContentMemory.lifecycle_status.in_(KNOWLEDGE_ELIGIBLE_STATUSES),
        )
        .order_by(
            ContentMemory.publish_time.desc().nullslast(),
            ContentMemory.id.desc(),
        )
        .limit(predictor.PERCENTILE_WINDOW)
    )
    videos = list((await db.execute(stmt)).scalars().all())

    hits = 0
    fails = 0
    skipped = 0

    for video in videos:
        views = video.performance.views if video.performance else 0
        classification = classify_video(
            views,
            p25=benchmarks.p25,
            p75=benchmarks.p75,
        )
        if classification is None:
            skipped += 1
            continue

        existing = await db.execute(
            select(KnowledgeEvolution).where(KnowledgeEvolution.video_id == video.id)
        )
        if existing.scalar_one_or_none() is not None:
            skipped += 1
            continue

        await analyze_video(
            db,
            account,
            video,
            classification,
            avg_view=benchmarks.avg_view,
            llm_client=llm_client,
        )
        if classification == KnowledgeType.HIT:
            hits += 1
        else:
            fails += 1

    return {"hits": hits, "fails": fails, "skipped": skipped}
