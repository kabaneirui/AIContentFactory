from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account
from app.models import Account
from app.schemas.learning import BrainLearningResponse
from app.schemas.profile import AccountProfileResponse, AccountProfileUpdate
from app.services import brain_learner

router = APIRouter(tags=["learning"])


@router.get(
    "/accounts/{account_id}/learning/latest",
    response_model=BrainLearningResponse,
)
async def get_latest_learning(
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> BrainLearningResponse:
    learning = await brain_learner.get_latest_learning(db, account.id)
    if learning is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No learning report found for account {account.id}",
        )
    return learning


@router.get(
    "/accounts/{account_id}/profile",
    response_model=AccountProfileResponse,
)
async def get_account_profile(
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> AccountProfileResponse:
    profile = await brain_learner.get_account_profile(db, account.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No profile found for account {account.id}",
        )
    return profile


@router.patch(
    "/accounts/{account_id}/profile",
    response_model=AccountProfileResponse,
)
async def update_account_profile(
    payload: AccountProfileUpdate,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> AccountProfileResponse:
    profile = await brain_learner.get_account_profile(db, account.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No profile found for account {account.id}",
        )
    if payload.locked_fields is not None:
        profile.locked_fields = payload.locked_fields
    await db.flush()
    return profile
