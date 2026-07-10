from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.trend import (
    TrendImportRequest,
    TrendImportResult,
    TrendTopicCreate,
    TrendTopicListResponse,
    TrendTopicResponse,
    TrendTopicUpdate,
)
from app.services import trend_service

router = APIRouter(tags=["trends"])


def _to_response(
    record,
    direction,
) -> TrendTopicResponse:
    data = TrendTopicResponse.model_validate(record)
    return data.model_copy(update={"trend_direction": direction})


@router.post(
    "/trends",
    response_model=TrendTopicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trend(
    payload: TrendTopicCreate,
    db: AsyncSession = Depends(get_db),
) -> TrendTopicResponse:
    record = await trend_service.create_trend(db, payload)
    return TrendTopicResponse.model_validate(record)


@router.get("/trends", response_model=TrendTopicListResponse)
async def list_trends(
    db: AsyncSession = Depends(get_db),
    category: str | None = None,
    season: str | None = None,
    festival: str | None = None,
    source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TrendTopicListResponse:
    items, total = await trend_service.list_trends(
        db,
        category=category,
        season=season,
        festival=festival,
        source=source,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return TrendTopicListResponse(
        items=[_to_response(record, direction) for record, direction in items],
        total=total,
    )


@router.get("/trends/{trend_id}", response_model=TrendTopicResponse)
async def get_trend(
    trend_id: int,
    db: AsyncSession = Depends(get_db),
) -> TrendTopicResponse:
    record = await trend_service.get_trend_by_id(db, trend_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend {trend_id} not found",
        )
    from app.services import trend_analyzer

    direction = await trend_analyzer.resolve_trend_direction(db, record)
    return _to_response(record, direction)


@router.patch("/trends/{trend_id}", response_model=TrendTopicResponse)
async def update_trend(
    trend_id: int,
    payload: TrendTopicUpdate,
    db: AsyncSession = Depends(get_db),
) -> TrendTopicResponse:
    record = await trend_service.get_trend_by_id(db, trend_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend {trend_id} not found",
        )
    updated = await trend_service.update_trend(db, record, payload)
    from app.services import trend_analyzer

    direction = await trend_analyzer.resolve_trend_direction(db, updated)
    return _to_response(updated, direction)


@router.delete("/trends/{trend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trend(
    trend_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    record = await trend_service.get_trend_by_id(db, trend_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend {trend_id} not found",
        )
    await trend_service.delete_trend(db, record)


@router.post(
    "/trends/import",
    response_model=TrendImportResult,
)
async def import_trends_json(
    payload: TrendImportRequest,
    db: AsyncSession = Depends(get_db),
) -> TrendImportResult:
    return await trend_service.import_trends_json(db, payload)


@router.post(
    "/trends/import/csv",
    response_model=TrendImportResult,
)
async def import_trends_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> TrendImportResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )
    content = (await file.read()).decode("utf-8-sig")
    try:
        raw_rows = trend_service.parse_csv_content(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return await trend_service.import_trends_from_rows(db, raw_rows)
