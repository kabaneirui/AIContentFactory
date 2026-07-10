from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account
from app.models import Account
from app.schemas.decision import DecideTodayRequest, DecideTodayResponse
from app.services import decision_center
from app.services.decision_center import DecisionCenterError

router = APIRouter(tags=["decision"])


@router.post(
    "/accounts/{account_id}/decide/today",
    response_model=DecideTodayResponse,
)
async def decide_today(
    payload: DecideTodayRequest,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> DecideTodayResponse:
    try:
        return await decision_center.decide_today(db, account, payload)
    except DecisionCenterError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
