from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_account
from app.models import Account
from app.schemas import AccountCreate, AccountResponse, AccountUpdate
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    db: AsyncSession = Depends(get_db),
) -> Account:
    return await account_service.create_account(db, payload)


@router.get("", response_model=list[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)) -> list[Account]:
    return await account_service.list_accounts(db)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account: Account = Depends(get_account)) -> Account:
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    payload: AccountUpdate,
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> Account:
    return await account_service.update_account(db, account, payload)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account: Account = Depends(get_account),
    db: AsyncSession = Depends(get_db),
) -> None:
    await account_service.delete_account(db, account)
