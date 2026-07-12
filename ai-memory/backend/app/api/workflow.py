from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account
from app.models import Account
from app.schemas.workflow import GenerateScriptRequest, GenerateScriptResponse
from app.services import content_generator

router = APIRouter(tags=["workflow"])


@router.post(
    "/accounts/{account_id}/workflow/generate-script",
    response_model=GenerateScriptResponse,
    summary="从决策选题生成口播稿",
)
async def generate_script(
    payload: GenerateScriptRequest,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> GenerateScriptResponse:
    return await content_generator.generate_script(db, account, payload)
