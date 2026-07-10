from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account
from app.models import Account
from app.schemas.prompt import (
    PromptActivateResponse,
    PromptCompareResponse,
    PromptEvolveRequest,
    PromptEvolveResponse,
    PromptVersionCreate,
    PromptVersionListResponse,
    PromptVersionResponse,
)
from app.services import prompt_evolver
from app.services.prompt_evolver import PromptEvolutionError

router = APIRouter(tags=["prompts"])


@router.get(
    "/accounts/{account_id}/prompts",
    response_model=PromptVersionListResponse,
)
async def list_prompt_versions(
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionListResponse:
    versions = await prompt_evolver.refresh_all_version_stats(db, account.id)
    if not versions:
        await prompt_evolver.ensure_initial_prompt_version(db, account)
        versions = await prompt_evolver.list_prompt_versions(db, account.id)

    active = await prompt_evolver.get_active_prompt_version(db, account.id)
    return PromptVersionListResponse(
        items=versions,
        active_version=active.version if active else None,
    )


@router.get(
    "/accounts/{account_id}/prompts/active",
    response_model=PromptVersionResponse,
)
async def get_active_prompt(
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionResponse:
    active = await prompt_evolver.get_active_prompt_version(db, account.id)
    if active is None:
        active = await prompt_evolver.ensure_initial_prompt_version(db, account)
    await prompt_evolver.refresh_version_stats(db, active)
    return active


@router.post(
    "/accounts/{account_id}/prompts",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_version(
    payload: PromptVersionCreate,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionResponse:
    return await prompt_evolver.create_prompt_version(
        db,
        account,
        prompt_content=payload.prompt_content,
        change_log=payload.change_log,
        activate=payload.activate,
    )


@router.post(
    "/accounts/{account_id}/prompts/evolve",
    response_model=PromptEvolveResponse,
)
async def evolve_prompt(
    payload: PromptEvolveRequest,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PromptEvolveResponse:
    try:
        evolved, reason, new_version, pending = await prompt_evolver.evolve_prompt_for_account(
            db,
            account,
            force=payload.force,
        )
    except PromptEvolutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return PromptEvolveResponse(
        evolved=evolved,
        reason=reason,
        new_version=new_version,
        pending_review=pending,
    )


@router.post(
    "/accounts/{account_id}/prompts/{version_id}/activate",
    response_model=PromptActivateResponse,
)
async def activate_prompt_version(
    version_id: int,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PromptActivateResponse:
    try:
        activated, previous = await prompt_evolver.activate_prompt_version(
            db,
            account.id,
            version_id,
        )
    except PromptEvolutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return PromptActivateResponse(
        activated_version=activated.version,
        previous_version=previous,
    )


@router.post(
    "/accounts/{account_id}/prompts/{version_id}/rollback",
    response_model=PromptActivateResponse,
)
async def rollback_prompt_version(
    version_id: int,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PromptActivateResponse:
    """回滚：将指定历史版本设为活跃版本。"""
    return await activate_prompt_version(version_id, account, db)


@router.get(
    "/accounts/{account_id}/prompts/compare",
    response_model=PromptCompareResponse,
)
async def compare_prompt_versions(
    version_a: str,
    version_b: str,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PromptCompareResponse:
    a = await prompt_evolver.get_prompt_version_by_label(db, account.id, version_a)
    b = await prompt_evolver.get_prompt_version_by_label(db, account.id, version_b)
    if a is None or b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both prompt versions not found",
        )
    await prompt_evolver.refresh_version_stats(db, a)
    await prompt_evolver.refresh_version_stats(db, b)
    return PromptCompareResponse(
        version_a=a,
        version_b=b,
        view_delta=b.avg_view - a.avg_view,
        finish_rate_delta=b.avg_finish_rate - a.avg_finish_rate,
        recommend_delta=b.recommend_score - a.recommend_score,
    )
