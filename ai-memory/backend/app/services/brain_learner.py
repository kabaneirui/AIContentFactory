"""Brain Learning：统计引擎 + LLM 报告 + Account Profile 刷新。"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from statistics import mean

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Account,
    AccountProfile,
    BrainLearning,
    ContentMemory,
    LifecycleStatus,
)
from app.prompts.brain_learning import (
    BRAIN_LEARNING_SYSTEM_PROMPT,
    build_brain_learning_user_prompt,
)
from app.schemas.learning import (
    DimensionRanking,
    HookCtaCombo,
    LearningReportContent,
    LearningStatsSnapshot,
)
from app.services import lifecycle as lifecycle_service
from app.services.llm_client import OpenAiCompatibleClient, get_llm_client

logger = logging.getLogger(__name__)

LEARNING_ELIGIBLE_STATUSES = {
    LifecycleStatus.TAGGED,
    LifecycleStatus.LEARNED,
    LifecycleStatus.SYNCING,
    LifecycleStatus.PUBLISHED,
}

PROFILE_FIELD_NAMES = (
    "platform",
    "account_type",
    "best_category",
    "best_scene",
    "best_duration",
    "best_publish_time",
    "best_cta",
    "best_hook",
    "best_knowledge_source",
)


class BrainLearningError(Exception):
    pass


@dataclass(frozen=True)
class VideoSample:
    video: ContentMemory
    views: int


def resolve_sample_window(total_eligible: int) -> int:
    """按文档与计划：默认 30；样本 >100 用 60；>300 用 100。"""
    if total_eligible <= 0:
        return 0
    if total_eligible > 300:
        return min(100, total_eligible)
    if total_eligible > 100:
        return min(60, total_eligible)
    return min(30, total_eligible)


def _dna_value(video: ContentMemory, key: str) -> str | None:
    if not video.dna_tags:
        return None
    value = video.dna_tags.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _title_prefix(video: ContentMemory) -> str | None:
    hook = _dna_value(video, "hook_type") or (video.hook or "").strip()
    if hook:
        return f"{hook}……"
    title = (video.title or "").strip()
    if len(title) >= 4:
        return f"{title[:4]}……"
    return title or None


def _publish_hour_label(video: ContentMemory) -> str | None:
    if video.publish_time is None:
        return None
    return f"{video.publish_time.hour:02d}:00"


def _avg_views(samples: list[VideoSample]) -> float:
    if not samples:
        return 0.0
    return mean(sample.views for sample in samples)


def _group_ranking(
    samples: list[VideoSample],
    key_fn,
) -> list[DimensionRanking]:
    groups: dict[str, list[VideoSample]] = defaultdict(list)
    for sample in samples:
        key = key_fn(sample.video)
        if key:
            groups[key].append(sample)

    ranking = [
        DimensionRanking(
            name=name,
            avg_view=round(_avg_views(items), 1),
            count=len(items),
        )
        for name, items in groups.items()
    ]
    ranking.sort(key=lambda item: item.avg_view, reverse=True)
    return ranking


def _hook_cta_ranking(samples: list[VideoSample]) -> list[HookCtaCombo]:
    groups: dict[tuple[str, str], list[VideoSample]] = defaultdict(list)
    for sample in samples:
        hook = _dna_value(sample.video, "hook_type") or (sample.video.hook or "").strip()
        cta = _dna_value(sample.video, "cta") or (sample.video.cta or "").strip()
        if hook and cta:
            groups[(hook, cta)].append(sample)

    combos = [
        HookCtaCombo(
            hook=hook,
            cta=cta,
            avg_view=round(_avg_views(items), 1),
            count=len(items),
        )
        for (hook, cta), items in groups.items()
    ]
    combos.sort(key=lambda item: item.avg_view, reverse=True)
    return combos


def compute_statistics(
    samples: list[VideoSample],
    *,
    total_eligible: int,
) -> LearningStatsSnapshot:
    return LearningStatsSnapshot(
        sample_size=len(samples),
        total_eligible=total_eligible,
        avg_view=round(_avg_views(samples), 1),
        template_ranking=_group_ranking(
            samples,
            lambda v: _dna_value(v, "template") or v.template,
        ),
        title_prefix_ranking=_group_ranking(samples, _title_prefix),
        scene_ranking=_group_ranking(
            samples,
            lambda v: _dna_value(v, "scene") or v.scene_style,
        ),
        publish_hour_ranking=_group_ranking(samples, _publish_hour_label),
        hook_cta_combos=_hook_cta_ranking(samples),
        knowledge_ranking=_group_ranking(
            samples,
            lambda v: _dna_value(v, "knowledge") or v.knowledge_source,
        ),
        cta_ranking=_group_ranking(
            samples,
            lambda v: _dna_value(v, "cta") or v.cta,
        ),
        hook_ranking=_group_ranking(
            samples,
            lambda v: _dna_value(v, "hook_type") or v.hook,
        ),
    )


def _format_duration_range(samples: list[VideoSample]) -> str | None:
    durations = [
        sample.video.duration
        for sample in samples
        if sample.video.duration is not None
    ]
    if not durations:
        return None
    if len(durations) == 1:
        return f"{durations[0]} 秒"

    sorted_samples = sorted(samples, key=lambda s: s.views, reverse=True)
    top_count = max(1, len(sorted_samples) // 4)
    top_durations = [
        sample.video.duration
        for sample in sorted_samples[:top_count]
        if sample.video.duration is not None
    ]
    if not top_durations:
        return f"{min(durations)}–{max(durations)} 秒"
    return f"{min(top_durations)}–{max(top_durations)} 秒"


def _infer_account_type(stats: LearningStatsSnapshot) -> str:
    if stats.knowledge_ranking and stats.knowledge_ranking[0].name in {
        "黄帝内经",
        "经络",
        "养阳",
        "养心",
    }:
        return "知识型账号"
    if stats.template_ranking and stats.template_ranking[0].name == "情绪":
        return "情绪型账号"
    return "养生内容账号"


def _derive_profile_values(
    account: Account,
    stats: LearningStatsSnapshot,
    samples: list[VideoSample],
) -> dict[str, str | None]:
    best_hour = stats.publish_hour_ranking[0].name if stats.publish_hour_ranking else None
    if best_hour and best_hour.endswith(":00"):
        hour = int(best_hour.split(":")[0])
        best_publish_time = f"{hour:02d}:30"
    else:
        best_publish_time = best_hour

    return {
        "platform": account.platform,
        "account_type": _infer_account_type(stats),
        "best_category": (
            stats.template_ranking[0].name if stats.template_ranking else None
        ),
        "best_scene": stats.scene_ranking[0].name if stats.scene_ranking else None,
        "best_duration": _format_duration_range(samples),
        "best_publish_time": best_publish_time,
        "best_cta": stats.cta_ranking[0].name if stats.cta_ranking else None,
        "best_hook": stats.hook_ranking[0].name if stats.hook_ranking else None,
        "best_knowledge_source": (
            stats.knowledge_ranking[0].name if stats.knowledge_ranking else None
        ),
    }


def _build_rule_based_report(
    stats: LearningStatsSnapshot,
    samples: list[VideoSample],
) -> LearningReportContent:
    top_template = stats.template_ranking[0] if stats.template_ranking else None
    weak_template = stats.template_ranking[-1] if stats.template_ranking else None
    top_scene = stats.scene_ranking[0] if stats.scene_ranking else None
    top_hour = stats.publish_hour_ranking[0] if stats.publish_hour_ranking else None

    summary_parts = [
        f"最近 {stats.sample_size} 条视频平均播放 {stats.avg_view:.0f}。"
    ]
    if top_template:
        summary_parts.append(
            f"「{top_template.name}」模板表现最好，均值 {top_template.avg_view:.0f}。"
        )

    strength_parts = []
    if top_template:
        strength_parts.append(
            f"内容模板「{top_template.name}」平均播放 {top_template.avg_view:.0f}"
        )
    if top_scene:
        strength_parts.append(
            f"画面「{top_scene.name}」平均播放 {top_scene.avg_view:.0f}"
        )
    if stats.hook_cta_combos:
        combo = stats.hook_cta_combos[0]
        strength_parts.append(
            f"Hook+CTA 组合「{combo.hook}+{combo.cta}」转化较好"
        )

    weakness_parts = []
    if weak_template and top_template and weak_template.name != top_template.name:
        weakness_parts.append(
            f"「{weak_template.name}」模板均值仅 {weak_template.avg_view:.0f}"
        )
    if len(stats.publish_hour_ranking) > 1:
        weak_hour = stats.publish_hour_ranking[-1]
        weakness_parts.append(f"{weak_hour.name} 时段发布效果偏弱")

    trend_text = _compute_trend_text(samples)

    suggestion_parts = []
    if top_template:
        suggestion_parts.append(f"优先使用「{top_template.name}」模板")
    if top_scene:
        suggestion_parts.append(f"保持「{top_scene.name}」画面风格")
    if top_hour:
        suggestion_parts.append(f"建议在 {top_hour.name} 前后发布")
    if weak_template and top_template and weak_template.name != top_template.name:
        suggestion_parts.append(f"减少「{weak_template.name}」类内容占比")

    optimization_parts = [
        "强化高播放模板与 Hook 组合",
        "优化弱时段发布策略",
        "保持画面风格与账号优势一致",
    ]

    return LearningReportContent(
        summary="".join(summary_parts),
        strength="；".join(strength_parts) or "样本数据不足，暂无明显优势",
        weakness="；".join(weakness_parts) or "暂无明显短板",
        trend=trend_text,
        suggestion="；".join(suggestion_parts) or "继续积累样本后重试",
        optimization="；".join(optimization_parts),
    )


def _publish_time_sort_key(sample: VideoSample) -> float:
    publish_time = sample.video.publish_time
    if publish_time is None:
        return 0.0
    if publish_time.tzinfo is None:
        publish_time = publish_time.replace(tzinfo=UTC)
    return publish_time.timestamp()


def _compute_trend_text(samples: list[VideoSample]) -> str:
    dated = [
        sample
        for sample in samples
        if sample.video.publish_time is not None
    ]
    if len(dated) < 4:
        return "样本量有限，趋势判断需更多数据支撑"

    dated.sort(key=_publish_time_sort_key)
    midpoint = len(dated) // 2
    older = dated[:midpoint]
    newer = dated[midpoint:]
    older_avg = _avg_views(older)
    newer_avg = _avg_views(newer)
    if newer_avg > older_avg * 1.1:
        return (
            f"近期播放呈上升趋势（前半段均值 {older_avg:.0f}，"
            f"后半段 {newer_avg:.0f}）"
        )
    if newer_avg < older_avg * 0.9:
        return (
            f"近期播放呈下滑趋势（前半段均值 {older_avg:.0f}，"
            f"后半段 {newer_avg:.0f}）"
        )
    return f"播放整体平稳（前半段 {older_avg:.0f}，后半段 {newer_avg:.0f}）"


async def _generate_report_content(
    account: Account,
    stats: LearningStatsSnapshot,
    samples: list[VideoSample],
    *,
    llm_client: OpenAiCompatibleClient | None = None,
) -> LearningReportContent:
    client = llm_client or get_llm_client()
    if not client.is_configured:
        logger.info(
            "LLM not configured; using rule-based learning report for account %s",
            account.id,
        )
        return _build_rule_based_report(stats, samples)

    user_prompt = build_brain_learning_user_prompt(
        account_name=account.name,
        platform=account.platform,
        sample_size=stats.sample_size,
        stats_json=json.dumps(stats.model_dump(), ensure_ascii=False, indent=2),
    )
    try:
        raw = await client.complete_json(
            system=BRAIN_LEARNING_SYSTEM_PROMPT,
            user=user_prompt,
        )
        return LearningReportContent.model_validate(raw)
    except (ValidationError, ValueError, KeyError) as exc:
        logger.warning(
            "Invalid LLM learning report for account %s: %s; falling back to rules",
            account.id,
            exc,
        )
        return _build_rule_based_report(stats, samples)
    except Exception as exc:
        logger.warning(
            "LLM learning report failed for account %s: %s; falling back to rules",
            account.id,
            exc,
        )
        return _build_rule_based_report(stats, samples)


async def count_eligible_samples(db: AsyncSession, account_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(ContentMemory)
        .where(
            ContentMemory.account_id == account_id,
            ContentMemory.dna_tags.is_not(None),
            ContentMemory.lifecycle_status.in_(LEARNING_ELIGIBLE_STATUSES),
        )
    )
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def fetch_learning_samples(
    db: AsyncSession,
    account_id: int,
    sample_size: int,
) -> list[VideoSample]:
    stmt = (
        select(ContentMemory)
        .options(selectinload(ContentMemory.performance))
        .where(
            ContentMemory.account_id == account_id,
            ContentMemory.dna_tags.is_not(None),
            ContentMemory.lifecycle_status.in_(LEARNING_ELIGIBLE_STATUSES),
        )
        .order_by(
            ContentMemory.publish_time.desc().nullslast(),
            ContentMemory.id.desc(),
        )
        .limit(sample_size)
    )
    result = await db.execute(stmt)
    videos = list(result.scalars().all())

    samples: list[VideoSample] = []
    for video in videos:
        views = video.performance.views if video.performance else 0
        samples.append(VideoSample(video=video, views=views))
    return samples


async def refresh_account_profile(
    db: AsyncSession,
    account: Account,
    stats: LearningStatsSnapshot,
    samples: list[VideoSample],
) -> AccountProfile:
    derived = _derive_profile_values(account, stats, samples)
    profile = account.profile
    if profile is None:
        profile = AccountProfile(account_id=account.id)
        db.add(profile)
        await db.flush()

    locked = set(profile.locked_fields or [])
    for field_name in PROFILE_FIELD_NAMES:
        if field_name in locked:
            continue
        setattr(profile, field_name, derived.get(field_name))

    await db.flush()
    return profile


def _mark_samples_learned(samples: list[VideoSample]) -> None:
    for sample in samples:
        if sample.video.lifecycle_status == LifecycleStatus.TAGGED:
            sample.video.lifecycle_status = lifecycle_service.transition(
                sample.video.lifecycle_status,
                LifecycleStatus.LEARNED,
            )


def _latest_prompt_version(samples: list[VideoSample]) -> str | None:
    for sample in samples:
        if sample.video.prompt:
            return sample.video.prompt
    return None


async def run_learning_for_account(
    db: AsyncSession,
    account_id: int,
    *,
    learning_date: date | None = None,
    llm_client: OpenAiCompatibleClient | None = None,
) -> BrainLearning:
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if account is None:
        raise BrainLearningError(f"Account {account_id} not found")

    total_eligible = await count_eligible_samples(db, account_id)
    window = resolve_sample_window(total_eligible)
    if window == 0:
        raise BrainLearningError(
            f"Account {account_id} has no eligible learning samples (need DNA-tagged videos)"
        )

    samples = await fetch_learning_samples(db, account_id, window)
    stats = compute_statistics(samples, total_eligible=total_eligible)
    report = await _generate_report_content(
        account,
        stats,
        samples,
        llm_client=llm_client,
    )

    target_date = learning_date or datetime.now(UTC).date()
    learning = BrainLearning(
        account_id=account_id,
        learning_date=target_date,
        sample_size=stats.sample_size,
        summary=report.summary,
        strength=report.strength,
        weakness=report.weakness,
        trend=report.trend,
        suggestion=report.suggestion,
        optimization=report.optimization,
        prompt_version=_latest_prompt_version(samples),
        stats_snapshot=stats.model_dump(),
    )
    db.add(learning)

    await refresh_account_profile(db, account, stats, samples)
    _mark_samples_learned(samples)

    from app.services import knowledge_analyzer, strategy_optimizer

    try:
        await knowledge_analyzer.run_knowledge_evolution_for_account(db, account_id)
    except Exception:
        logger.exception(
            "Knowledge evolution failed for account %s",
            account_id,
        )
    try:
        await strategy_optimizer.run_strategy_optimizer_for_account(db, account_id)
    except Exception:
        logger.exception(
            "Strategy optimizer failed for account %s",
            account_id,
        )

    from app.services import prompt_evolver

    try:
        await prompt_evolver.run_prompt_evolution_for_account(db, account_id)
    except Exception:
        logger.exception(
            "Prompt evolution failed for account %s",
            account_id,
        )

    await db.flush()
    return learning


async def get_latest_learning(
    db: AsyncSession,
    account_id: int,
) -> BrainLearning | None:
    stmt = (
        select(BrainLearning)
        .where(BrainLearning.account_id == account_id)
        .order_by(BrainLearning.learning_date.desc(), BrainLearning.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_account_profile(
    db: AsyncSession,
    account_id: int,
) -> AccountProfile | None:
    stmt = select(AccountProfile).where(AccountProfile.account_id == account_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def run_daily_learning_for_all_accounts(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(Account.id))
    account_ids = list(result.scalars().all())

    processed = 0
    skipped = 0
    failed = 0

    for account_id in account_ids:
        try:
            await run_learning_for_account(db, account_id)
            processed += 1
        except BrainLearningError as exc:
            logger.info("Skip learning for account %s: %s", account_id, exc)
            skipped += 1
        except Exception:
            logger.exception("Learning failed for account %s", account_id)
            failed += 1

    return {"processed": processed, "skipped": skipped, "failed": failed}
