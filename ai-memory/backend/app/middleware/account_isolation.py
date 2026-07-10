import logging
from collections.abc import Callable

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from app.database import account_id_ctx
from app.models.base import AccountScopedMixin

logger = logging.getLogger(__name__)


def _apply_account_filter(execute_state: ORMExecuteState) -> None:
    """Inject account_id filter for all AccountScoped model queries."""
    account_id = account_id_ctx.get()
    if account_id is None:
        return

    if not execute_state.is_select:
        return

    if execute_state.is_column_load or execute_state.is_relationship_load:
        return

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            AccountScopedMixin,
            lambda cls: cls.account_id == account_id,  # type: ignore[attr-defined]
            include_aliases=True,
        )
    )


@event.listens_for(Session, "do_orm_execute")
def _on_do_orm_execute(execute_state: ORMExecuteState) -> None:
    _apply_account_filter(execute_state)


@event.listens_for(AsyncSession.sync_session_class, "do_orm_execute")
def _on_async_do_orm_execute(execute_state: ORMExecuteState) -> None:
    _apply_account_filter(execute_state)


def set_account_context(account_id: int | None) -> None:
    account_id_ctx.set(account_id)


def get_account_context() -> int | None:
    return account_id_ctx.get()


def enforce_account_scope_on_write(instance: object) -> None:
    """Ensure writes on account-scoped models use the current account context."""
    account_id = account_id_ctx.get()
    if account_id is None:
        return

    mapper = inspect(instance.__class__)
    if not issubclass(mapper.class_, AccountScopedMixin):
        return

    current = getattr(instance, "account_id", None)
    if current is None:
        instance.account_id = account_id  # type: ignore[attr-defined]
    elif current != account_id:
        raise PermissionError(
            f"Cross-account write blocked: resource account_id={current}, "
            f"context account_id={account_id}"
        )


class AccountIsolationMiddleware:
    """Extract account_id from URL path and activate isolation context."""

    ACCOUNT_PATH_PREFIX = "/accounts/"

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        token = None

        if path.startswith(self.ACCOUNT_PATH_PREFIX):
            parts = path[len(self.ACCOUNT_PATH_PREFIX) :].split("/")
            if parts and parts[0].isdigit():
                token = account_id_ctx.set(int(parts[0]))
                logger.debug("Account isolation context set: account_id=%s", parts[0])

        try:
            await self.app(scope, receive, send)
        finally:
            if token is not None:
                account_id_ctx.reset(token)
