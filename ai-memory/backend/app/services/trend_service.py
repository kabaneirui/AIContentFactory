"""TrendTopic CRUD 与 CSV/JSON 批量导入。"""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend_topic import TrendTopic
from app.schemas.trend import (
    TrendDirection,
    TrendImportError,
    TrendImportRequest,
    TrendImportResult,
    TrendImportRow,
    TrendTopicCreate,
    TrendTopicUpdate,
)
from app.services import trend_analyzer

CSV_FIELD_ALIASES: dict[str, str] = {
    "heat": "heat_score",
    "heatscore": "heat_score",
    "date": "trend_date",
    "trenddate": "trend_date",
}


def _normalize_header(header: str) -> str:
    key = header.strip().lower().replace(" ", "_")
    return CSV_FIELD_ALIASES.get(key, key)


def _parse_row_dict(
    raw: dict[str, Any],
    row_num: int,
) -> tuple[TrendImportRow | None, TrendImportError | None]:
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        if key is None:
            continue
        norm_key = _normalize_header(str(key))
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue
        normalized[norm_key] = value

    try:
        return TrendImportRow.model_validate(normalized), None
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first.get("loc", ()))
        return None, TrendImportError(
            row=row_num,
            field=field or None,
            message=first["msg"],
        )


def parse_csv_content(content: str) -> list[tuple[int, dict[str, Any]]]:
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise ValueError("CSV file has no header row")
    return [(idx, row) for idx, row in enumerate(reader, start=2)]


def parse_json_content(content: str) -> list[tuple[int, dict[str, Any]]]:
    data = json.loads(content)
    if isinstance(data, dict) and "trends" in data:
        items = data["trends"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("JSON must be an array or an object with a 'trends' array")

    if not isinstance(items, list) or not items:
        raise ValueError("Import payload must contain at least one trend")

    rows: list[tuple[int, dict[str, Any]]] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Row {idx}: expected an object")
        rows.append((idx, item))
    return rows


async def create_trend(
    db: AsyncSession,
    payload: TrendTopicCreate,
) -> TrendTopic:
    record = TrendTopic(
        topic=payload.topic.strip(),
        category=payload.category,
        heat_score=payload.heat_score,
        source=payload.source,
        trend_date=payload.trend_date or date.today(),
        season=payload.season,
        festival=payload.festival,
    )
    db.add(record)
    await db.flush()
    return record


async def get_trend_by_id(
    db: AsyncSession,
    trend_id: int,
) -> TrendTopic | None:
    result = await db.execute(select(TrendTopic).where(TrendTopic.id == trend_id))
    return result.scalar_one_or_none()


async def update_trend(
    db: AsyncSession,
    record: TrendTopic,
    payload: TrendTopicUpdate,
) -> TrendTopic:
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(record, key, value)
    await db.flush()
    return record


async def delete_trend(db: AsyncSession, record: TrendTopic) -> None:
    await db.delete(record)
    await db.flush()


async def list_trends(
    db: AsyncSession,
    *,
    category: str | None = None,
    season: str | None = None,
    festival: str | None = None,
    source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
    include_direction: bool = True,
) -> tuple[list[tuple[TrendTopic, TrendDirection | None]], int]:
    filters = []
    if category:
        filters.append(TrendTopic.category == category)
    if season:
        filters.append(TrendTopic.season == season)
    if festival:
        filters.append(TrendTopic.festival == festival)
    if source:
        filters.append(TrendTopic.source == source)
    if date_from:
        filters.append(TrendTopic.trend_date >= date_from)
    if date_to:
        filters.append(TrendTopic.trend_date <= date_to)

    count_stmt = select(func.count()).select_from(TrendTopic)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = select(TrendTopic).order_by(
        TrendTopic.trend_date.desc(),
        TrendTopic.heat_score.desc(),
        TrendTopic.id.desc(),
    )
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    if not include_direction:
        return [(record, None) for record in records], total

    enriched = await trend_analyzer.enrich_with_direction(db, records)
    return enriched, total


async def import_trends_from_rows(
    db: AsyncSession,
    rows: list[tuple[int, dict[str, Any]]],
) -> TrendImportResult:
    imported = 0
    skipped = 0
    errors: list[TrendImportError] = []

    for row_num, raw in rows:
        parsed, error = _parse_row_dict(raw, row_num)
        if error:
            errors.append(error)
            continue
        if parsed is None:
            skipped += 1
            continue

        await create_trend(db, TrendTopicCreate.model_validate(parsed.model_dump()))
        imported += 1

    return TrendImportResult(imported=imported, skipped=skipped, errors=errors)


async def import_trends_json(
    db: AsyncSession,
    payload: TrendImportRequest,
) -> TrendImportResult:
    rows = [(idx, item.model_dump()) for idx, item in enumerate(payload.trends, start=1)]
    return await import_trends_from_rows(db, rows)
