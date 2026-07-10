"""Account-scoped data isolation tests."""

import pytest
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, account_id_ctx
from app.middleware.account_isolation import enforce_account_scope_on_write
from app.models import Account
from app.models.base import AccountScopedMixin


class _SampleContent(Base, AccountScopedMixin):
    __tablename__ = "test_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)


@pytest.mark.asyncio
async def test_account_scoped_query_filter(db_session: AsyncSession):
    account_a = Account(name="A", platform="douyin")
    account_b = Account(name="B", platform="douyin")
    db_session.add_all([account_a, account_b])
    await db_session.flush()

    db_session.add_all(
        [
            _SampleContent(account_id=account_a.id, title="A-1"),
            _SampleContent(account_id=account_b.id, title="B-1"),
        ]
    )
    await db_session.flush()

    token = account_id_ctx.set(account_a.id)
    try:
        result = await db_session.execute(select(_SampleContent))
        rows = list(result.scalars().all())
        assert len(rows) == 1
        assert rows[0].title == "A-1"
    finally:
        account_id_ctx.reset(token)


@pytest.mark.asyncio
async def test_enforce_account_scope_on_write_blocks_cross_account(
    db_session: AsyncSession,
):
    account_a = Account(name="A", platform="douyin")
    account_b = Account(name="B", platform="douyin")
    db_session.add_all([account_a, account_b])
    await db_session.flush()

    content = _SampleContent(account_id=account_b.id, title="B-1")
    token = account_id_ctx.set(account_a.id)
    try:
        with pytest.raises(PermissionError):
            enforce_account_scope_on_write(content)
    finally:
        account_id_ctx.reset(token)


@pytest.mark.asyncio
async def test_enforce_account_scope_on_write_sets_account_id(db_session: AsyncSession):
    account = Account(name="A", platform="douyin")
    db_session.add(account)
    await db_session.flush()

    content = _SampleContent(title="new")
    token = account_id_ctx.set(account.id)
    try:
        enforce_account_scope_on_write(content)
        assert content.account_id == account.id
    finally:
        account_id_ctx.reset(token)
