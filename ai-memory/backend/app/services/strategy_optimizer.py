"""Strategy Optimizer：失败归因聚合与策略调整建议。"""

from __future__ import annotations

import logging
from collections import Counter
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AccountProfile,
    BrainLearning,
    ContentMemory,
    KnowledgeEvolution,
    KnowledgeType,
)
from app.schemas.knowledge import StrategyOptimization
from app.services import brain_learner, predictor

logger = logging.getLogger(__name__)

ATTRIBUTION_LABELS = {
    "weak_opening": "前三秒弱",
    "scene_repetition": "画面重复",
    "weak_hook": "Hook 太平",
    "low_knowledge_value": "知识获得感不足",
    "duration_mismatch": "时长不匹配",
    "bad_publish_time": "发布时间不佳",
}


def _parse_duration_range(best_duration: str | None) -> tuple[int, int] | None:
    if not best_duration:
        return None
    text = best_duration.replace("秒", "").strip()
    if "–" in text:
        parts = text.split("–")
    elif "-" in text:
        parts = text.split("-")
    else:
        return None
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except (ValueError, IndexError):
        return None


def _dna_value(video: ContentMemory, key: str) -> str | None:
    if not video.dna_tags:
        return None
    value = video.dna_tags.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def attribute_failure(
    video: ContentMemory,
    profile: AccountProfile | None,
    *,
    recent_fail_scenes: list[str],
) -> list[str]:
    reasons: list[str] = []

    perf = video.performance
    if perf and perf.rate_3s is not None and perf.rate_3s < 0.35:
        reasons.append("weak_opening")

    scene = _dna_value(video, "scene") or video.scene_style
    if scene and recent_fail_scenes.count(scene) >= 2:
        reasons.append("scene_repetition")

    hook = _dna_value(video, "hook_type") or video.hook
    if profile and profile.best_hook and hook and hook != profile.best_hook:
        weak_hooks = {"你知道吗", "其实", "今天来说"}
        if hook in weak_hooks or len(hook) <= 3:
            reasons.append("weak_hook")

    knowledge = _dna_value(video, "knowledge") or video.knowledge_source
    template = _dna_value(video, "template") or video.template
    if template == "情绪" or knowledge in {"养生常识", None, ""}:
        reasons.append("low_knowledge_value")

    duration_range = _parse_duration_range(profile.best_duration if profile else None)
    if duration_range and video.duration is not None:
        low, high = duration_range
        if video.duration < low - 5 or video.duration > high + 10:
            reasons.append("duration_mismatch")

    if profile and profile.best_publish_time and video.publish_time:
        best_hour = int(profile.best_publish_time.split(":")[0])
        publish_hour = video.publish_time.hour
        if abs(publish_hour - best_hour) >= 4:
            reasons.append("bad_publish_time")

    return reasons


def build_strategy_optimization(
    failure_counts: Counter[str],
    profile: AccountProfile | None,
    learning: BrainLearning | None,
) -> StrategyOptimization:
    failure_reasons = [
        ATTRIBUTION_LABELS[key]
        for key, _count in failure_counts.most_common()
        if key in ATTRIBUTION_LABELS
    ]

    increase: list[str] = []
    decrease: list[str] = []
    optimize: list[str] = []

    if profile:
        if profile.best_category:
            increase.append(f"{profile.best_category}模板")
        if profile.best_hook:
            optimize.append(f"强化「{profile.best_hook}」类 Hook 冲击力")
        if profile.best_scene:
            increase.append(f"{profile.best_scene}画面差异化")
        if profile.best_knowledge_source:
            increase.append(f"{profile.best_knowledge_source}知识来源")

    if "weak_opening" in failure_counts:
        optimize.append("优化前三秒留存与开头钩子")
    if "scene_repetition" in failure_counts:
        optimize.append("轮换画面风格，避免同质化")
    if "weak_hook" in failure_counts:
        optimize.append("提升 Hook 冲击力与悬念感")
    if "low_knowledge_value" in failure_counts:
        increase.append("口诀模板、数字化标题")
        decrease.append("情绪类内容")
    if "duration_mismatch" in failure_counts and profile and profile.best_duration:
        optimize.append(f"控制时长在 {profile.best_duration}")
    if "bad_publish_time" in failure_counts and profile and profile.best_publish_time:
        optimize.append(f"优先在 {profile.best_publish_time} 前后发布")

    if learning and learning.suggestion:
        for part in learning.suggestion.split("；"):
            text = part.strip()
            if text and text not in increase:
                increase.append(text)

    if not decrease:
        decrease.append("低播放情绪类内容")

    summary_parts = []
    if failure_reasons:
        summary_parts.append(f"近期主要失败归因：{'、'.join(failure_reasons[:4])}")
    else:
        summary_parts.append("近期失败样本较少，建议保持优势模板并持续观察")
    if increase:
        summary_parts.append(f"建议增加：{'、'.join(increase[:3])}")

    return StrategyOptimization(
        failure_reasons=failure_reasons,
        increase=list(dict.fromkeys(increase))[:5],
        decrease=list(dict.fromkeys(decrease))[:3],
        optimize=list(dict.fromkeys(optimize))[:5],
        summary="；".join(summary_parts),
    )


def format_optimization_text(strategy: StrategyOptimization) -> str:
    lines = [strategy.summary, ""]
    if strategy.failure_reasons:
        lines.append("近期失败原因：")
        for index, reason in enumerate(strategy.failure_reasons, start=1):
            lines.append(f"{index}. {reason}")
        lines.append("")
    lines.append("策略调整建议：")
    if strategy.increase:
        lines.append(f"- 增加：{'、'.join(strategy.increase)}")
    if strategy.decrease:
        lines.append(f"- 减少：{'、'.join(strategy.decrease)}")
    if strategy.optimize:
        lines.append(f"- 优化：{'、'.join(strategy.optimize)}")
    return "\n".join(lines)


async def run_strategy_optimizer_for_account(
    db: AsyncSession,
    account_id: int,
) -> StrategyOptimization | None:
    learning = await brain_learner.get_latest_learning(db, account_id)
    profile = await brain_learner.get_account_profile(db, account_id)

    cutoff = datetime.now(UTC) - timedelta(days=30)
    stmt = (
        select(KnowledgeEvolution)
        .options(
            selectinload(KnowledgeEvolution.video).selectinload(
                ContentMemory.performance
            )
        )
        .where(
            KnowledgeEvolution.account_id == account_id,
            KnowledgeEvolution.knowledge_type == KnowledgeType.FAIL,
            KnowledgeEvolution.created_at >= cutoff,
        )
    )
    fail_entries = list((await db.execute(stmt)).scalars().all())
    if not fail_entries:
        if learning is None:
            return None
        strategy = StrategyOptimization(
            failure_reasons=[],
            increase=[profile.best_category] if profile and profile.best_category else [],
            decrease=["情绪类内容"],
            optimize=["保持账号优势模板"],
            summary="暂无足够失败样本，沿用学习报告建议",
        )
        learning.optimization = format_optimization_text(strategy)
        await db.flush()
        return strategy

    failure_counts: Counter[str] = Counter()
    recent_scenes: list[str] = []
    for entry in fail_entries:
        video = entry.video
        scene = _dna_value(video, "scene") or video.scene_style
        if scene:
            recent_scenes.append(scene)
        for reason in attribute_failure(video, profile, recent_fail_scenes=recent_scenes):
            failure_counts[reason] += 1

    strategy = build_strategy_optimization(failure_counts, profile, learning)
    if learning is not None:
        learning.optimization = format_optimization_text(strategy)
        await db.flush()
    return strategy
