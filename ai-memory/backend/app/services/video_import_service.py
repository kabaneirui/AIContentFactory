import csv
import io
import json
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, ContentMemory, ContentPerformance
from app.schemas.video import (
    VideoImportError,
    VideoImportRequest,
    VideoImportResult,
    VideoImportRow,
)
from app.services import lifecycle as lifecycle_service
from app.services.video_service import schedule_performance_syncs

from app.models.content_memory import LifecycleStatus

CSV_FIELD_ALIASES: dict[str, str] = {
    "video_id": "platform_video_id",
    "platformvideoid": "platform_video_id",
    "knowledge": "knowledge_source",
    "knowledgesource": "knowledge_source",
    "scene": "scene_style",
    "scenestyle": "scene_style",
    "publish_time": "publish_time",
    "publishtime": "publish_time",
    "view": "views",
    "like": "likes",
    "comment": "comments",
    "share": "shares",
    "collect": "collects",
    "forward": "forwards",
    "3s_rate": "rate_3s",
    "3srate": "rate_3s",
    "rate3s": "rate_3s",
}

PERFORMANCE_FIELDS = {
    "views",
    "ctr",
    "rate_3s",
    "finish_rate",
    "average_watch",
    "likes",
    "comments",
    "shares",
    "collects",
    "forwards",
    "fans_increase",
    "reach_level",
    "recommend_rate",
    "engagement_rate",
}


def _normalize_header(header: str) -> str:
    key = header.strip().lower().replace(" ", "_")
    return CSV_FIELD_ALIASES.get(key, key)


def _parse_row_dict(raw: dict[str, Any], row_num: int) -> tuple[VideoImportRow | None, VideoImportError | None]:
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        if key is None:
            continue
        norm_key = _normalize_header(str(key))
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue
        normalized[norm_key] = value

    try:
        return VideoImportRow.model_validate(normalized), None
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first.get("loc", ()))
        return None, VideoImportError(row=row_num, field=field or None, message=first["msg"])


def parse_csv_content(content: str) -> list[tuple[int, dict[str, Any]]]:
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise ValueError("CSV file has no header row")
    return [(idx, row) for idx, row in enumerate(reader, start=2)]


def parse_json_content(content: str) -> list[tuple[int, dict[str, Any]]]:
    data = json.loads(content)
    if isinstance(data, dict) and "videos" in data:
        items = data["videos"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("JSON must be an array or an object with a 'videos' array")

    if not isinstance(items, list) or not items:
        raise ValueError("Import payload must contain at least one video")

    rows: list[tuple[int, dict[str, Any]]] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Row {idx}: expected an object")
        rows.append((idx, item))
    return rows


async def import_videos_from_rows(
    db: AsyncSession,
    account: Account,
    rows: list[VideoImportRow],
) -> VideoImportResult:
    imported = 0
    skipped = 0
    errors: list[VideoImportError] = []
    video_ids: list[int] = []

    for row_num, row in enumerate(rows, start=1):
        if row.platform_video_id:
            from sqlalchemy import select

            existing = await db.execute(
                select(ContentMemory).where(
                    ContentMemory.account_id == account.id,
                    ContentMemory.platform_video_id == row.platform_video_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                errors.append(
                    VideoImportError(
                        row=row_num,
                        field="platform_video_id",
                        message=f"Duplicate platform_video_id: {row.platform_video_id}",
                    )
                )
                continue

        perf_data = {
            field: getattr(row, field)
            for field in PERFORMANCE_FIELDS
            if getattr(row, field) is not None
        }
        video_data = row.model_dump(exclude=PERFORMANCE_FIELDS)

        if video_data.get("platform") is None:
            video_data["platform"] = account.platform

        status = lifecycle_service.initial_status_for_video(
            has_publish_time=video_data.get("publish_time") is not None
        )

        video = ContentMemory(**video_data, account_id=account.id, lifecycle_status=status)
        db.add(video)
        await db.flush()

        if perf_data:
            performance = ContentPerformance(content_memory_id=video.id, **perf_data)
            db.add(performance)

        if status == LifecycleStatus.PUBLISHED:
            await schedule_performance_syncs(db, video)

        video_ids.append(video.id)
        imported += 1

    return VideoImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
        video_ids=video_ids,
    )


async def import_videos_json(
    db: AsyncSession,
    account: Account,
    payload: VideoImportRequest,
) -> VideoImportResult:
    return await import_videos_from_rows(db, account, payload.videos)


async def import_videos_from_parsed_rows(
    db: AsyncSession,
    account: Account,
    raw_rows: list[tuple[int, dict[str, Any]]],
) -> VideoImportResult:
    parsed_rows: list[VideoImportRow] = []
    errors: list[VideoImportError] = []

    for row_num, raw in raw_rows:
        row, error = _parse_row_dict(raw, row_num)
        if error is not None:
            errors.append(error)
            continue
        assert row is not None
        parsed_rows.append(row)

    if not parsed_rows and errors:
        return VideoImportResult(imported=0, skipped=0, errors=errors)

    result = await import_videos_from_rows(db, account, parsed_rows)
    result.errors = errors + result.errors
    return result
