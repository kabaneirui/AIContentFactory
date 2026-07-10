from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account
from app.models import Account, KnowledgeType
from app.schemas.knowledge import KnowledgeEvolutionResponse, KnowledgeListResponse
from app.services import knowledge_analyzer

router = APIRouter(tags=["knowledge"])


@router.get(
    "/accounts/{account_id}/knowledge",
    response_model=KnowledgeListResponse,
)
async def list_knowledge(
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
    type: str | None = Query(default=None, alias="type", pattern="^(hit|fail)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> KnowledgeListResponse:
    knowledge_type = KnowledgeType(type) if type else None
    items, total = await knowledge_analyzer.list_knowledge(
        db,
        account.id,
        knowledge_type=knowledge_type,
        limit=limit,
        offset=offset,
    )
    return KnowledgeListResponse(
        items=[KnowledgeEvolutionResponse.model_validate(item) for item in items],
        total=total,
    )
