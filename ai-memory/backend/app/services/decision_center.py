"""Decision Center：70% 账号经验 + 30% 全网热点综合决策。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, AccountProfile, BrainLearning, KnowledgeEvolution, KnowledgeType
from app.prompts.decision import DECISION_SYSTEM_PROMPT, build_decision_user_prompt
from app.schemas.decision import DecideTodayRequest, DecideTodayResponse, DecisionRecommendation
from app.schemas.prediction import PredictRequest
from app.schemas.trend import TrendDirection
from app.services import brain_learner, knowledge_analyzer, predictor, strategy_optimizer, trend_analyzer
from app.services.llm_client import OpenAiCompatibleClient, get_llm_client

logger = logging.getLogger(__name__)

ACCOUNT_WEIGHT = 0.7
TREND_WEIGHT = 0.3
DEFAULT_PUBLISH_TIME = "19:30"


class DecisionCenterError(Exception):
    pass


@dataclass(frozen=True)
class CandidateSpec:
    title: str
    template: str
    hook: str
    knowledge_source: str
    scene_style: str
    duration: int
    cta: str
    matched_trend: str | None = None
    trend_direction: TrendDirection | None = None
    trend_heat: float | None = None


def _parse_best_duration(profile: AccountProfile | None) -> int:
    if profile is None or not profile.best_duration:
        return 32
    text = profile.best_duration.replace("秒", "").strip()
    if "–" in text:
        parts = text.split("–")
    elif "-" in text:
        parts = text.split("-")
    else:
        return 32
    try:
        low = int(parts[0].strip())
        high = int(parts[1].strip())
        return (low + high) // 2
    except (ValueError, IndexError):
        return 32


def _default_profile_fields(profile: AccountProfile | None) -> dict[str, str]:
    return {
        "hook": (profile.best_hook if profile else None) or "老祖宗",
        "knowledge": (profile.best_knowledge_source if profile else None) or "黄帝内经",
        "template": (profile.best_category if profile else None) or "口诀",
        "scene": (profile.best_scene if profile else None) or "古风",
        "cta": (profile.best_cta if profile else None) or "收藏",
    }


def _format_trend_title(
    hook: str,
    knowledge: str,
    trend_topic: str,
    *,
    season: str | None,
    festival: str | None,
) -> str:
    if season and season in trend_topic:
        return f"{hook}：{trend_topic}"
    if festival and festival in trend_topic:
        return f"{festival}｜{trend_topic}"
    return f"{hook}：{knowledge}{trend_topic}"


def _build_rule_candidates(
    profile: AccountProfile | None,
    trends: list[tuple],
    hits: list[KnowledgeEvolution],
    *,
    season: str | None,
    festival: str | None,
    count: int,
) -> list[CandidateSpec]:
    fields = _default_profile_fields(profile)
    duration = _parse_best_duration(profile)
    specs: list[CandidateSpec] = []
    seen_titles: set[str] = set()

    def add(spec: CandidateSpec) -> None:
        key = spec.title.strip()
        if key in seen_titles:
            return
        seen_titles.add(key)
        specs.append(spec)

    for trend_record, direction in trends[:3]:
        title = _format_trend_title(
            fields["hook"],
            fields["knowledge"],
            trend_record.topic,
            season=season,
            festival=festival,
        )
        add(
            CandidateSpec(
                title=title,
                template=fields["template"],
                hook=fields["hook"],
                knowledge_source=trend_record.category or fields["knowledge"],
                scene_style=fields["scene"],
                duration=duration,
                cta=fields["cta"],
                matched_trend=trend_record.topic,
                trend_direction=direction,
                trend_heat=trend_record.heat_score,
            )
        )

    add(
        CandidateSpec(
            title=f"{fields['hook']}留下来的{fields['knowledge']}{fields['template']}",
            template=fields["template"],
            hook=fields["hook"],
            knowledge_source=fields["knowledge"],
            scene_style=fields["scene"],
            duration=duration,
            cta=fields["cta"],
        )
    )

    if season:
        add(
            CandidateSpec(
                title=f"{fields['knowledge']}：{season}养生{fields['template']}",
                template=fields["template"],
                hook=fields["hook"],
                knowledge_source=fields["knowledge"],
                scene_style=fields["scene"],
                duration=duration,
                cta=fields["cta"],
                matched_trend=season,
            )
        )

    if festival:
        add(
            CandidateSpec(
                title=f"{festival}｜{fields['hook']}的{fields['knowledge']}小贴士",
                template=fields["template"],
                hook=fields["hook"],
                knowledge_source=fields["knowledge"],
                scene_style=fields["scene"],
                duration=duration,
                cta=fields["cta"],
                matched_trend=festival,
            )
        )

    for hit in hits[:2]:
        title = hit.analysis_text.split("。")[0][:40] if hit.analysis_text else None
        if not title:
            continue
        add(
            CandidateSpec(
                title=title,
                template=fields["template"],
                hook=fields["hook"],
                knowledge_source=fields["knowledge"],
                scene_style=fields["scene"],
                duration=duration,
                cta=fields["cta"],
            )
        )

    add(
        CandidateSpec(
            title=f"很多人不知道的{fields['knowledge']}{fields['template']}",
            template="动作" if fields["template"] == "口诀" else fields["template"],
            hook="很多人",
            knowledge_source=fields["knowledge"],
            scene_style="实拍" if fields["scene"] == "古风" else fields["scene"],
            duration=duration + 8,
            cta=fields["cta"],
        )
    )

    return specs[:count]


def _account_weight_score(
    dna_tags: dict[str, str],
    profile: AccountProfile | None,
    duration: int | None,
) -> float:
    match = predictor._profile_match_score(dna_tags, profile)
    duration_match = predictor._duration_match_score(duration, profile)
    return round(match * 0.75 + duration_match * 0.25, 3)


def _trend_weight_score(
    spec: CandidateSpec,
    *,
    max_heat: float,
) -> float:
    if spec.matched_trend is None or spec.trend_heat is None:
        return 0.35

    direction = spec.trend_direction or TrendDirection.STABLE
    heat_norm = spec.trend_heat / max_heat if max_heat > 0 else 0.5
    heat_norm = max(0.0, min(1.0, heat_norm))
    direction_bonus = {
        TrendDirection.RISING: 0.15,
        TrendDirection.STABLE: 0.0,
        TrendDirection.FALLING: -0.1,
    }[direction]
    return round(max(0.0, min(1.0, heat_norm + direction_bonus)), 3)


def _build_rule_reasons(
    spec: CandidateSpec,
    profile: AccountProfile | None,
    learning: BrainLearning | None,
    *,
    account_score: float,
    trend_score: float,
    predict_view: int,
    predict_level: int,
    season: str | None,
    festival: str | None,
) -> list[str]:
    reasons: list[str] = []

    if profile and profile.best_category:
        if spec.template == profile.best_category:
            reasons.append(f"✓ 账号{profile.best_category}类内容平均播放最高")
        else:
            reasons.append(f"· 尝试非优势模板「{spec.template}」以探索多样性")

    if spec.matched_trend and spec.trend_direction:
        label = trend_analyzer.trend_direction_label(spec.trend_direction)
        reasons.append(f"✓ 热点「{spec.matched_trend}」全网热度{label}")

    if season and spec.matched_trend and season in (spec.matched_trend, spec.title):
        reasons.append(f"✓ 契合当前节气「{season}」")

    if festival and (festival in spec.title or spec.matched_trend == festival):
        reasons.append(f"✓ 契合当前节日「{festival}」")

    if learning and learning.weakness:
        reasons.append(f"· 注意规避近期短板：{learning.weakness[:60]}")

    if learning and learning.strength:
        reasons.append(f"✓ 账号优势：{learning.strength[:60]}")

    reasons.append(
        f"· 综合评分 {account_score * ACCOUNT_WEIGHT + trend_score * TREND_WEIGHT:.2f}"
        f"（账号 {account_score:.2f} ×70% + 热点 {trend_score:.2f} ×30%）"
    )
    reasons.append(f"✓ 预计播放 {predict_view}，预测等级 {predict_level} 星")

    return reasons[:6]


async def _generate_llm_candidates(
    account: Account,
    *,
    count: int,
    season: str | None,
    festival: str | None,
    platform: str | None,
    profile: AccountProfile | None,
    learning: BrainLearning | None,
    trends: list[tuple],
    hits: list[KnowledgeEvolution],
    strategy_text: str | None,
    llm_client: OpenAiCompatibleClient,
) -> list[CandidateSpec] | None:
    profile_json = json.dumps(
        {
            "best_category": profile.best_category if profile else None,
            "best_hook": profile.best_hook if profile else None,
            "best_scene": profile.best_scene if profile else None,
            "best_knowledge_source": profile.best_knowledge_source if profile else None,
            "best_duration": profile.best_duration if profile else None,
            "best_publish_time": profile.best_publish_time if profile else None,
            "best_cta": profile.best_cta if profile else None,
        },
        ensure_ascii=False,
    )
    learning_json = json.dumps(
        {
            "summary": learning.summary if learning else None,
            "strength": learning.strength if learning else None,
            "weakness": learning.weakness if learning else None,
            "suggestion": learning.suggestion if learning else None,
            "optimization": learning.optimization if learning else None,
        },
        ensure_ascii=False,
    )
    trends_json = json.dumps(
        [
            {
                "topic": record.topic,
                "category": record.category,
                "heat_score": record.heat_score,
                "direction": direction.value,
            }
            for record, direction in trends
        ],
        ensure_ascii=False,
    )
    hits_json = json.dumps(
        [
            {
                "analysis": hit.analysis_text[:120],
                "dimension_scores": hit.dimension_scores,
            }
            for hit in hits[:5]
        ],
        ensure_ascii=False,
    )
    user_prompt = build_decision_user_prompt(
        count=count,
        season=season,
        festival=festival,
        platform=platform or account.platform,
        profile_json=profile_json,
        learning_json=learning_json,
        trends_json=trends_json,
        hit_samples_json=hits_json,
        strategy_json=strategy_text or "暂无策略优化建议",
    )
    try:
        raw = await llm_client.complete_json(
            system=DECISION_SYSTEM_PROMPT,
            user=user_prompt,
        )
        candidates = raw.get("candidates")
        if not isinstance(candidates, list):
            return None

        specs: list[CandidateSpec] = []
        fields = _default_profile_fields(profile)
        duration = _parse_best_duration(profile)
        for item in candidates[:count]:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            specs.append(
                CandidateSpec(
                    title=title.strip(),
                    template=str(item.get("template") or fields["template"]),
                    hook=str(item.get("hook") or fields["hook"]),
                    knowledge_source=str(
                        item.get("knowledge_source") or fields["knowledge"]
                    ),
                    scene_style=str(item.get("scene_style") or fields["scene"]),
                    duration=int(item.get("duration") or duration),
                    cta=str(item.get("cta") or fields["cta"]),
                    matched_trend=item.get("matched_trend"),
                )
            )
        return specs or None
    except Exception as exc:
        logger.warning("LLM decision candidates failed for account %s: %s", account.id, exc)
        return None


async def decide_today(
    db: AsyncSession,
    account: Account,
    request: DecideTodayRequest,
    *,
    llm_client: OpenAiCompatibleClient | None = None,
) -> DecideTodayResponse:
    profile = await brain_learner.get_account_profile(db, account.id)
    learning = await brain_learner.get_latest_learning(db, account.id)
    hits, _ = await knowledge_analyzer.list_knowledge(
        db,
        account.id,
        knowledge_type=KnowledgeType.HIT,
        limit=5,
    )
    trends = await trend_analyzer.get_matching_trends(
        db,
        season=request.season,
        festival=request.festival,
        limit=10,
    )
    max_heat = await trend_analyzer.get_max_heat_score(db)

    strategy = None
    try:
        strategy = await strategy_optimizer.run_strategy_optimizer_for_account(
            db, account.id
        )
    except Exception as exc:
        logger.debug("Strategy optimizer skipped for account %s: %s", account.id, exc)

    client = llm_client or get_llm_client()
    specs: list[CandidateSpec] | None = None
    if client.is_configured:
        specs = await _generate_llm_candidates(
            account,
            count=request.count,
            season=request.season,
            festival=request.festival,
            platform=request.platform,
            profile=profile,
            learning=learning,
            trends=trends,
            hits=hits,
            strategy_text=(
                strategy_optimizer.format_optimization_text(strategy)
                if strategy
                else None
            ),
            llm_client=client,
        )

    if not specs:
        specs = _build_rule_candidates(
            profile,
            trends,
            hits,
            season=request.season,
            festival=request.festival,
            count=request.count,
        )

    if len(specs) < 3:
        raise DecisionCenterError(
            "Not enough context to generate recommendations; "
            "add account learning data or trend topics"
        )

    publish_time = (
        profile.best_publish_time if profile and profile.best_publish_time else DEFAULT_PUBLISH_TIME
    )

    recommendations: list[DecisionRecommendation] = []
    for spec in specs:
        predict_request = PredictRequest(
            title=spec.title,
            template=spec.template,
            hook=spec.hook,
            knowledge_source=spec.knowledge_source,
            scene_style=spec.scene_style,
            duration=spec.duration,
            cta=spec.cta,
        )
        prediction, dna_tags = await predictor.predict_content(
            db,
            account,
            predict_request,
            llm_client=client if client.is_configured else None,
        )
        account_score = _account_weight_score(dna_tags, profile, spec.duration)
        trend_score = _trend_weight_score(spec, max_heat=max_heat)
        combined = round(
            account_score * ACCOUNT_WEIGHT + trend_score * TREND_WEIGHT,
            3,
        )

        reasons = _build_rule_reasons(
            spec,
            profile,
            learning,
            account_score=account_score,
            trend_score=trend_score,
            predict_view=prediction.predict_view,
            predict_level=prediction.predict_level,
            season=request.season,
            festival=request.festival,
        )
        if prediction.reason:
            for reason in prediction.reason[:2]:
                if reason not in reasons:
                    reasons.insert(0, reason)

        recommendations.append(
            DecisionRecommendation(
                rank=0,
                title=spec.title,
                predict_level=prediction.predict_level,
                predict_view=prediction.predict_view,
                suggested_publish_time=publish_time,
                reasons=reasons[:6],
                account_weight_score=account_score,
                trend_weight_score=trend_score,
                combined_score=combined,
                matched_trend=spec.matched_trend,
                template=spec.template,
                hook=spec.hook,
                knowledge_source=spec.knowledge_source,
                scene_style=spec.scene_style,
                duration=spec.duration,
                cta=spec.cta,
            )
        )

    recommendations.sort(
        key=lambda item: (item.combined_score, item.predict_view),
        reverse=True,
    )
    for index, item in enumerate(recommendations, start=1):
        recommendations[index - 1] = item.model_copy(update={"rank": index})

    return DecideTodayResponse(
        account_id=account.id,
        generated_at=datetime.now(UTC),
        season=request.season,
        festival=request.festival,
        platform=request.platform or account.platform,
        recommendations=recommendations[: request.count],
    )
