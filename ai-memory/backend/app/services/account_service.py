from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account
from app.schemas import AccountCreate, AccountUpdate
from app.services import prompt_evolver


async def create_account(db: AsyncSession, payload: AccountCreate) -> Account:
    account = Account(name=payload.name, platform=payload.platform)
    db.add(account)
    await db.flush()
    await prompt_evolver.ensure_initial_prompt_version(db, account)
    await db.refresh(account)
    return account


async def list_accounts(db: AsyncSession) -> list[Account]:
    result = await db.execute(select(Account).order_by(Account.created_at.desc()))
    return list(result.scalars().all())


async def get_account_by_id(db: AsyncSession, account_id: int) -> Account | None:
    result = await db.execute(select(Account).where(Account.id == account_id))
    return result.scalar_one_or_none()


async def update_account(
    db: AsyncSession, account: Account, payload: AccountUpdate
) -> Account:
    if payload.name is not None:
        account.name = payload.name
    if payload.platform is not None:
        account.platform = payload.platform
    if payload.predict_threshold is not None:
        account.predict_threshold = payload.predict_threshold
    if payload.auto_evolve is not None:
        account.auto_evolve = payload.auto_evolve
    await db.flush()
    await db.refresh(account)
    return account


async def delete_account(db: AsyncSession, account: Account) -> None:
    await db.delete(account)
    await db.flush()
