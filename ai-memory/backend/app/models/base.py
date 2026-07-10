from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.database import Base


class AccountScopedMixin:
    """Mixin for models that belong to a single account.

    All queries on subclasses are automatically filtered by the current
    account_id from request context when account isolation is active.
    """

    @declared_attr
    def account_id(cls) -> Mapped[int]:  # noqa: N805
        return mapped_column(
            ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:  # noqa: N805
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )
