"""Trend 趋势分析：热点方向判断与决策匹配。"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend_topic import TrendTopic
from app.schemas.trend import TrendDirection

LOOKBACK_DAYS = 7
RISING_THRESHOLD = 1.1
FALLING_THRESHOLD = 0.9


def compute_direction(
    current_heat: float,
    historical_heats: list[float],
) -> TrendDirection:
    """对比当前热度与历史均值，判断上升/下降/平稳。"""
    if not historical_heats:
        return TrendDirection.STABLE

    avg_heat = sum(historical_heats) / len(historical_heats)
    if avg_heat <= 0:
        return TrendDirection.STABLE

    ratio = current_heat / avg_heat
    if ratio >= RISING_THRESHOLD:
        return TrendDirection.RISING
    if ratio <= FALLING_THRESHOLD:
        return TrendDirection.FALLING
    return TrendDirection.STABLE


async def get_topic_history(
    db: AsyncSession,
    topic: str,
    *,
    before_date: date,
    lookback_days: int = LOOKBACK_DAYS,
) -> list[TrendTopic]:
    start_date = before_date - timedelta(days=lookback_days)
    stmt = (
        select(TrendTopic)
        .where(
            TrendTopic.topic == topic,
            TrendTopic.trend_date >= start_date,
            TrendTopic.trend_date < before_date,
        )
        .order_by(TrendTopic.trend_date.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def resolve_trend_direction(
    db: AsyncSession,
    record: TrendTopic,
) -> TrendDirection:
    history = await get_topic_history(db, record.topic, before_date=record.trend_date)
    historical_heats = [item.heat_score for item in history]
    return compute_direction(record.heat_score, historical_heats)


def trend_direction_label(direction: TrendDirection) -> str:
    labels = {
        TrendDirection.RISING: "上升",
        TrendDirection.FALLING: "下降",
        TrendDirection.STABLE: "平稳",
    }
    return labels[direction]


def trend_score_from_record(
    record: TrendTopic,
    direction: TrendDirection,
    *,
    max_heat: float,
) -> float:
    """将热点记录归一化为 0-1 趋势分（含方向加成）。"""
    heat_norm = record.heat_score / max_heat if max_heat > 0 else 0.5
    heat_norm = max(0.0, min(1.0, heat_norm))

    direction_bonus = {
        TrendDirection.RISING: 0.15,
        TrendDirection.STABLE: 0.0,
        TrendDirection.FALLING: -0.1,
    }[direction]
    return max(0.0, min(1.0, heat_norm + direction_bonus))


async def get_matching_trends(
    db: AsyncSession,
    *,
    season: str | None = None,
    festival: str | None = None,
    category: str | None = None,
    limit: int = 10,
    reference_date: date | None = None,
) -> list[tuple[TrendTopic, TrendDirection]]:
    """按节气/节日/分类匹配热点，返回带趋势方向的记录。"""
    ref_date = reference_date or date.today()
    recent_start = ref_date - timedelta(days=14)

    filters = [TrendTopic.trend_date >= recent_start, TrendTopic.trend_date <= ref_date]
    if category:
        filters.append(TrendTopic.category == category)

    context_filters = []
    if season:
        context_filters.append(TrendTopic.season == season)
    if festival:
        context_filters.append(TrendTopic.festival == festival)

    if context_filters:
        filters.append(or_(*context_filters))

    stmt = (
        select(TrendTopic)
        .where(*filters)
        .order_by(TrendTopic.heat_score.desc(), TrendTopic.trend_date.desc())
        .limit(limit * 3)
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    if not records and (season or festival):
        fallback_stmt = (
            select(TrendTopic)
            .where(
                TrendTopic.trend_date >= recent_start,
                TrendTopic.trend_date <= ref_date,
            )
            .order_by(TrendTopic.heat_score.desc(), TrendTopic.trend_date.desc())
            .limit(limit * 3)
        )
        result = await db.execute(fallback_stmt)
        records = list(result.scalars().all())

    seen_topics: set[str] = set()
    matched: list[tuple[TrendTopic, TrendDirection]] = []
    for record in records:
        if record.topic in seen_topics:
            continue
        seen_topics.add(record.topic)
        direction = await resolve_trend_direction(db, record)
        matched.append((record, direction))
        if len(matched) >= limit:
            break

    return matched


async def enrich_with_direction(
    db: AsyncSession,
    records: list[TrendTopic],
) -> list[tuple[TrendTopic, TrendDirection]]:
    enriched: list[tuple[TrendTopic, TrendDirection]] = []
    for record in records:
        direction = await resolve_trend_direction(db, record)
        enriched.append((record, direction))
    return enriched


async def get_max_heat_score(
    db: AsyncSession,
    *,
    reference_date: date | None = None,
) -> float:
    ref_date = reference_date or date.today()
    recent_start = ref_date - timedelta(days=30)
    stmt = select(func.max(TrendTopic.heat_score)).where(
        TrendTopic.trend_date >= recent_start,
        TrendTopic.trend_date <= ref_date,
    )
    value = (await db.execute(stmt)).scalar_one_or_none()
    return float(value) if value else 100.0
