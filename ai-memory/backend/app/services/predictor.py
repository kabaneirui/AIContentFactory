"""Prediction Engine：规则加权 + LLM 理由生成 + PredictionHistory 持久化。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from statistics import mean

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Account,
    AccountProfile,
    BrainLearning,
    PredictionHistory,
)
from app.prompts.prediction import (
    PREDICTION_SYSTEM_PROMPT,
    build_prediction_user_prompt,
)
from app.schemas.prediction import PredictRequest, PredictionResult
from app.services import brain_learner
from app.services.llm_client import OpenAiCompatibleClient, get_llm_client

logger = logging.getLogger(__name__)

PERCENTILE_WINDOW = 30
MATCH_BONUS = 0.18
MISMATCH_PENALTY = 0.12


class PredictionError(Exception):
    pass


@dataclass(frozen=True)
class ViewBenchmarks:
    avg_view: float
    p25: float
    p75: float
    sample_count: int


def _percentile(sorted_values: list[int], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


async def compute_view_benchmarks(
    db: AsyncSession,
    account_id: int,
) -> ViewBenchmarks:
    samples = await brain_learner.fetch_learning_samples(
        db, account_id, sample_size=PERCENTILE_WINDOW
    )
    views = [sample.views for sample in samples if sample.views > 0]
    if not views:
        return ViewBenchmarks(avg_view=200.0, p25=100.0, p75=400.0, sample_count=0)

    sorted_views = sorted(views)
    return ViewBenchmarks(
        avg_view=mean(views),
        p25=_percentile(sorted_views, 0.25),
        p75=_percentile(sorted_views, 0.75),
        sample_count=len(views),
    )


def resolve_threshold(account: Account, benchmarks: ViewBenchmarks) -> float:
    if account.predict_threshold is not None:
        return account.predict_threshold
    if benchmarks.sample_count > 0:
        return benchmarks.p25
    return benchmarks.avg_view * 0.5


def _infer_dna_tags(request: PredictRequest) -> dict[str, str]:
    if request.dna_tags:
        return dict(request.dna_tags)

    template = request.template or "口诀"
    hook = request.hook or "很多人"
    knowledge = request.knowledge_source or "养生常识"
    scene = request.scene_style or "实拍"
    cta = request.cta or "收藏"
    title = request.title
    title_type = "口诀型" if "口诀" in title else "疑问型" if "？" in title else "陈述型"

    return {
        "title_type": title_type,
        "hook_type": hook,
        "template": template,
        "knowledge": knowledge,
        "emotion": "获得感",
        "scene": scene,
        "pacing": "快切",
        "cta": cta,
    }


def _profile_match_score(
    dna_tags: dict[str, str],
    profile: AccountProfile | None,
) -> float:
    if profile is None:
        return 0.5

    checks = [
        (dna_tags.get("template"), profile.best_category),
        (dna_tags.get("hook_type"), profile.best_hook),
        (dna_tags.get("scene"), profile.best_scene),
        (dna_tags.get("knowledge"), profile.best_knowledge_source),
        (dna_tags.get("cta"), profile.best_cta),
    ]
    score = 0.5
    for actual, best in checks:
        if not actual or not best:
            continue
        if actual == best:
            score += MATCH_BONUS
        else:
            score -= MISMATCH_PENALTY
    return max(0.2, min(1.0, score))


def _duration_match_score(
    duration: int | None,
    profile: AccountProfile | None,
) -> float:
    if duration is None or profile is None or not profile.best_duration:
        return 0.5

    text = profile.best_duration.replace("秒", "").strip()
    if "–" in text:
        parts = text.split("–")
    elif "-" in text:
        parts = text.split("-")
    else:
        return 0.5

    try:
        low = int(parts[0].strip())
        high = int(parts[1].strip())
    except (ValueError, IndexError):
        return 0.5

    if low <= duration <= high:
        return 1.0
    margin = max(10, (high - low) // 2)
    distance = min(abs(duration - low), abs(duration - high))
    return max(0.3, 1.0 - distance / margin)


def _predict_finish_rate(
    dna_tags: dict[str, str],
    samples: list[brain_learner.VideoSample],
) -> float:
    template = dna_tags.get("template")
    rates: list[float] = []
    for sample in samples:
        if sample.video.performance and sample.video.performance.finish_rate is not None:
            video_template = (
                sample.video.dna_tags.get("template")
                if sample.video.dna_tags
                else sample.video.template
            )
            if template and video_template == template:
                rates.append(sample.video.performance.finish_rate)

    if rates:
        return round(mean(rates), 4)
    all_rates = [
        sample.video.performance.finish_rate
        for sample in samples
        if sample.video.performance and sample.video.performance.finish_rate is not None
    ]
    if all_rates:
        return round(mean(all_rates), 4)
    return 0.25


def _predict_level(predict_view: int, avg_view: float) -> int:
    if avg_view <= 0:
        ratio = 1.0
    else:
        ratio = predict_view / avg_view
    if ratio >= 1.3:
        return 5
    if ratio >= 1.1:
        return 4
    if ratio >= 0.9:
        return 3
    if ratio >= 0.7:
        return 2
    return 1


def _compute_confidence(sample_count: int, profile: AccountProfile | None) -> float:
    base = 0.35 + min(sample_count, PERCENTILE_WINDOW) / PERCENTILE_WINDOW * 0.45
    if profile is not None:
        base += 0.1
    return round(min(0.95, base), 2)


def _build_rule_reasons(
    dna_tags: dict[str, str],
    profile: AccountProfile | None,
    *,
    predict_view: int,
    threshold: float,
    passed: bool,
    learning: BrainLearning | None,
) -> list[str]:
    reasons: list[str] = []

    def check(field: str | None, best: str | None, label: str) -> None:
        if not field or not best:
            return
        if field == best:
            reasons.append(f"✓ 符合账号最佳{label}「{best}」")
        else:
            reasons.append(f"✗ {label}「{field}」与账号优势「{best}」不匹配")

    if profile:
        check(dna_tags.get("template"), profile.best_category, "模板")
        check(dna_tags.get("hook_type"), profile.best_hook, "Hook")
        check(dna_tags.get("knowledge"), profile.best_knowledge_source, "知识来源")
        check(dna_tags.get("scene"), profile.best_scene, "画面")
        check(dna_tags.get("cta"), profile.best_cta, "CTA")

    if learning and learning.strength:
        reasons.append(f"✓ 账号优势：{learning.strength[:80]}")
    if learning and learning.weakness and not passed:
        reasons.append(f"✗ 近期短板：{learning.weakness[:80]}")

    if passed:
        reasons.append(f"✓ 预计播放 {predict_view} 高于阈值 {threshold:.0f}")
    else:
        reasons.append(
            f"✗ 预计播放 {predict_view} 低于阈值 {threshold:.0f}，建议重新生成"
        )
    return reasons[:6]


async def _generate_reasons(
  account: Account,
  request: PredictRequest,
  dna_tags: dict[str, str],
  profile: AccountProfile | None,
  learning: BrainLearning | None,
  *,
  predict_view: int,
  predict_level: int,
  avg_view: float,
  threshold: float,
  passed: bool,
  llm_client: OpenAiCompatibleClient | None = None,
) -> list[str]:
    client = llm_client or get_llm_client()
    if not client.is_configured:
        return _build_rule_reasons(
            dna_tags,
            profile,
            predict_view=predict_view,
            threshold=threshold,
            passed=passed,
            learning=learning,
        )

    profile_json = json.dumps(
        {
            "best_category": profile.best_category if profile else None,
            "best_hook": profile.best_hook if profile else None,
            "best_scene": profile.best_scene if profile else None,
            "best_knowledge_source": (
                profile.best_knowledge_source if profile else None
            ),
            "best_cta": profile.best_cta if profile else None,
        },
        ensure_ascii=False,
    )
    user_prompt = build_prediction_user_prompt(
        title=request.title,
        dna_tags_json=json.dumps(dna_tags, ensure_ascii=False),
        profile_json=profile_json,
        learning_summary=learning.summary if learning else None,
        predict_view=predict_view,
        predict_level=predict_level,
        avg_view=avg_view,
    )
    try:
        raw = await client.complete_json(
            system=PREDICTION_SYSTEM_PROMPT,
            user=user_prompt,
        )
        reasons = raw.get("reason")
        if isinstance(reasons, list) and all(isinstance(item, str) for item in reasons):
            return reasons
    except Exception as exc:
        logger.warning(
            "LLM prediction reasons failed for account %s: %s",
            account.id,
            exc,
        )

    return _build_rule_reasons(
        dna_tags,
        profile,
        predict_view=predict_view,
        threshold=threshold,
        passed=passed,
        learning=learning,
    )


async def predict_content(
    db: AsyncSession,
    account: Account,
    request: PredictRequest,
    *,
    llm_client: OpenAiCompatibleClient | None = None,
) -> tuple[PredictionResult, dict[str, str]]:
    benchmarks = await compute_view_benchmarks(db, account.id)
    threshold = resolve_threshold(account, benchmarks)
    profile = await brain_learner.get_account_profile(db, account.id)
    learning = await brain_learner.get_latest_learning(db, account.id)
    samples = await brain_learner.fetch_learning_samples(
        db, account.id, sample_size=PERCENTILE_WINDOW
    )

    dna_tags = _infer_dna_tags(request)
    match_score = _profile_match_score(dna_tags, profile)
    duration_score = _duration_match_score(request.duration, profile)
    combined_score = match_score * 0.75 + duration_score * 0.25

    base_view = benchmarks.avg_view if benchmarks.sample_count > 0 else 200.0
    predict_view = max(1, int(base_view * combined_score))
    predict_finish_rate = _predict_finish_rate(dna_tags, samples)
    predict_level = _predict_level(predict_view, base_view)
    confidence = _compute_confidence(benchmarks.sample_count, profile)
    passed = predict_view >= threshold

    reasons = await _generate_reasons(
        account,
        request,
        dna_tags,
        profile,
        learning,
        predict_view=predict_view,
        predict_level=predict_level,
        avg_view=base_view,
        threshold=threshold,
        passed=passed,
        llm_client=llm_client,
    )

    result = PredictionResult(
        predict_view=predict_view,
        predict_finish_rate=predict_finish_rate,
        predict_level=predict_level,
        confidence=confidence,
        reason=reasons,
        threshold=round(threshold, 1),
        passed=passed,
    )
    return result, dna_tags


async def create_prediction(
    db: AsyncSession,
    account: Account,
    request: PredictRequest,
    *,
    llm_client: OpenAiCompatibleClient | None = None,
) -> tuple[PredictionHistory, PredictionResult]:
    result, dna_tags = await predict_content(
        db, account, request, llm_client=llm_client
    )
    record = PredictionHistory(
        account_id=account.id,
        title=request.title,
        predict_view=result.predict_view,
        predict_finish_rate=result.predict_finish_rate,
        confidence=result.confidence,
        predict_level=result.predict_level,
        reason=result.reason,
        dna_tags_snapshot=dna_tags,
        passed=result.passed,
        threshold_used=result.threshold,
    )
    db.add(record)
    await db.flush()
    return record, result


def compute_error_rate(predict_view: int, actual_view: int) -> float:
    if predict_view <= 0:
        return 1.0
    return round(abs(actual_view - predict_view) / predict_view, 4)


async def calibrate_prediction(
    db: AsyncSession,
    prediction: PredictionHistory,
    *,
    video_id: int | None,
    actual_view: int,
    actual_finish_rate: float | None,
) -> PredictionHistory:
    prediction.actual_view = actual_view
    prediction.actual_finish_rate = actual_finish_rate
    prediction.error_rate = compute_error_rate(
        prediction.predict_view,
        actual_view,
    )
    if video_id is not None:
        prediction.video_id = video_id
    await db.flush()
    return prediction


async def get_prediction_by_id(
    db: AsyncSession,
    prediction_id: int,
) -> PredictionHistory | None:
    result = await db.execute(
        select(PredictionHistory).where(PredictionHistory.id == prediction_id)
    )
    return result.scalar_one_or_none()
