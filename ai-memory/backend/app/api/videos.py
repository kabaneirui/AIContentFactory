from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account, get_video
from app.models import Account, ContentMemory, LifecycleStatus
from app.schemas.dna import BatchTagRequest, BatchTagResult, RetagResponse
from app.schemas.sync import SyncLogListResponse, SyncTriggerResponse
from app.schemas.video import (
    PerformanceUpdate,
    VideoCreate,
    VideoImportRequest,
    VideoImportResult,
    VideoListResponse,
    VideoResponse,
)
from app.services import dna_tagger, video_import_service, video_service
from app.services.dna_tagger import DnaTaggingError
from app.services.dna_trigger import schedule_video_tagging, schedule_videos_tagging

router = APIRouter(tags=["videos"])


async def _commit_import_result(
    db: AsyncSession,
    account: Account,
    result: VideoImportResult,
) -> VideoImportResult:
    """Persist import rows before scheduling background DNA tagging."""
    if result.imported <= 0:
        return result

    await db.commit()

    found = await db.scalar(
        select(func.count())
        .select_from(ContentMemory)
        .where(
            ContentMemory.account_id == account.id,
            ContentMemory.id.in_(result.video_ids),
        )
    )
    if found != len(result.video_ids):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Import commit verification failed: expected {len(result.video_ids)} "
                f"videos for account {account.id}, found {found or 0}"
            ),
        )
    return result


def _collect_dna_filters(
    dna_hook_type: str | None = None,
    dna_template: str | None = None,
    dna_scene: str | None = None,
    dna_knowledge: str | None = None,
    dna_emotion: str | None = None,
    dna_title_type: str | None = None,
    dna_pacing: str | None = None,
    dna_cta: str | None = None,
) -> dict[str, str] | None:
    mapping = {
        "hook_type": dna_hook_type,
        "template": dna_template,
        "scene": dna_scene,
        "knowledge": dna_knowledge,
        "emotion": dna_emotion,
        "title_type": dna_title_type,
        "pacing": dna_pacing,
        "cta": dna_cta,
    }
    filters = {key: value for key, value in mapping.items() if value is not None}
    return filters or None


@router.post(
    "/accounts/{account_id}/videos",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_video(
    payload: VideoCreate,
    background_tasks: BackgroundTasks,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> ContentMemory:
    video = await video_service.create_video(db, account, payload)
    background_tasks.add_task(schedule_video_tagging, video.id)
    return video


@router.get("/accounts/{account_id}/videos", response_model=VideoListResponse)
async def list_videos(
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    lifecycle_status: LifecycleStatus | None = None,
    category: str | None = None,
    template: str | None = None,
    keyword: str | None = None,
    dna_hook_type: str | None = None,
    dna_template: str | None = None,
    dna_scene: str | None = None,
    dna_knowledge: str | None = None,
    dna_emotion: str | None = None,
    dna_title_type: str | None = None,
    dna_pacing: str | None = None,
    dna_cta: str | None = None,
) -> VideoListResponse:
    items, total = await video_service.list_videos(
        db,
        account.id,
        page=page,
        page_size=page_size,
        lifecycle_status=lifecycle_status,
        category=category,
        template=template,
        keyword=keyword,
        dna_filters=_collect_dna_filters(
            dna_hook_type=dna_hook_type,
            dna_template=dna_template,
            dna_scene=dna_scene,
            dna_knowledge=dna_knowledge,
            dna_emotion=dna_emotion,
            dna_title_type=dna_title_type,
            dna_pacing=dna_pacing,
            dna_cta=dna_cta,
        ),
    )
    return VideoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/accounts/{account_id}/videos/import",
    response_model=VideoImportResult,
    status_code=status.HTTP_201_CREATED,
)
async def import_videos_json(
    payload: VideoImportRequest,
    background_tasks: BackgroundTasks,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> VideoImportResult:
    result = await video_import_service.import_videos_json(db, account, payload)
    result = await _commit_import_result(db, account, result)
    if result.video_ids:
        background_tasks.add_task(schedule_videos_tagging, result.video_ids)
    return result


@router.post(
    "/accounts/{account_id}/videos/import/csv",
    response_model=VideoImportResult,
    status_code=status.HTTP_201_CREATED,
)
async def import_videos_csv(
    background_tasks: BackgroundTasks,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> VideoImportResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )

    content = (await file.read()).decode("utf-8-sig")
    try:
        raw_rows = video_import_service.parse_csv_content(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    result = await video_import_service.import_videos_from_parsed_rows(
        db, account, raw_rows
    )
    result = await _commit_import_result(db, account, result)
    if result.video_ids:
        background_tasks.add_task(schedule_videos_tagging, result.video_ids)
    return result


@router.post(
    "/accounts/{account_id}/videos/batch-tag",
    response_model=BatchTagResult,
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_tag_videos(
    payload: BatchTagRequest,
    background_tasks: BackgroundTasks,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> BatchTagResult:
    video_ids = await dna_tagger.list_videos_for_batch_tag(
        db,
        account.id,
        video_ids=payload.video_ids,
        force=payload.force,
    )
    if not video_ids:
        return BatchTagResult(queued=0, video_ids=[])

    background_tasks.add_task(schedule_videos_tagging, video_ids, force=payload.force)
    return BatchTagResult(queued=len(video_ids), video_ids=video_ids)


@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(video: ContentMemory = Depends(get_video)) -> ContentMemory:
    return video


@router.post("/videos/{video_id}/retag", response_model=RetagResponse)
async def retag_video(
    video: ContentMemory = Depends(get_video),
    db: AsyncSession = Depends(get_db),
) -> RetagResponse:
    try:
        tags = await dna_tagger.tag_video(db, video, force=True)
    except DnaTaggingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return RetagResponse(
        video_id=video.id,
        dna_tags=tags.to_storage(),
        lifecycle_status=_lifecycle_value(video.lifecycle_status),
    )


def _lifecycle_value(status: LifecycleStatus | str) -> str:
    if isinstance(status, LifecycleStatus):
        return status.value
    return str(status)


@router.patch("/videos/{video_id}/performance", response_model=VideoResponse)
async def update_video_performance(
    payload: PerformanceUpdate,
    video: ContentMemory = Depends(get_video),
    db: AsyncSession = Depends(get_db),
) -> ContentMemory:
    await video_service.update_performance(db, video, payload)
    refreshed = await video_service.get_video_by_id(db, video.id)
    assert refreshed is not None
    return refreshed


@router.post("/videos/{video_id}/sync", response_model=SyncTriggerResponse)
async def trigger_video_sync(
    video: ContentMemory = Depends(get_video),
    db: AsyncSession = Depends(get_db),
) -> SyncTriggerResponse:
    """Trigger an immediate performance sync via the platform adapter (manual simulation)."""
    from app.models.sync_log import SyncLogStatus
    from app.services.performance_apply_service import get_account_for_video, sync_video_performance

    account = await get_account_for_video(db, video)
    sync_log = await sync_video_performance(db, video, account)
    return SyncTriggerResponse(
        video_id=video.id,
        sync_log=sync_log,
        performance_updated=sync_log.status == SyncLogStatus.SUCCESS,
    )


@router.get("/videos/{video_id}/sync-logs", response_model=SyncLogListResponse)
async def list_video_sync_logs(
    video: ContentMemory = Depends(get_video),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> SyncLogListResponse:
    from app.services.performance_apply_service import list_sync_logs_for_video

    items = await list_sync_logs_for_video(
        db, video.id, account_id=video.account_id, limit=limit
    )
    return SyncLogListResponse(items=items, total=len(items))
