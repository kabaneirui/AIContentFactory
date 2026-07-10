from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Account, ContentMemory, PredictionHistory
from app.services import video_service


async def get_account(
    account_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> Account:
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )
    return account


async def get_video(
    video_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> ContentMemory:
    video = await video_service.get_video_by_id(db, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found",
        )
    return video


async def get_prediction(
    prediction_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> PredictionHistory:
    from app.services import predictor

    prediction = await predictor.get_prediction_by_id(db, prediction_id)
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction {prediction_id} not found",
        )
    return prediction
