from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account, get_prediction
from app.models import Account, PredictionHistory
from app.schemas.prediction import (
    PredictApiResponse,
    PredictRequest,
    PredictionCalibrateRequest,
    PredictionResponse,
    PredictionResult,
)
from app.services import predictor

router = APIRouter(tags=["prediction"])


@router.post(
    "/accounts/{account_id}/predict",
    response_model=PredictApiResponse,
)
async def predict_content(
    payload: PredictRequest,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> PredictApiResponse:
    record, result = await predictor.create_prediction(db, account, payload)
    return PredictApiResponse(
        pass_=result.passed,
        prediction=result,
        prediction_id=record.id,
    )


@router.patch(
    "/predictions/{prediction_id}",
    response_model=PredictionResponse,
)
async def calibrate_prediction(
    payload: PredictionCalibrateRequest,
    prediction: PredictionHistory = Depends(get_prediction),
    db: AsyncSession = Depends(get_db),
) -> PredictionHistory:
    updated = await predictor.calibrate_prediction(
        db,
        prediction,
        video_id=payload.video_id,
        actual_view=payload.actual_view,
        actual_finish_rate=payload.actual_finish_rate,
    )
    await db.refresh(updated)
    return updated
