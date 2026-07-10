"""create sync logs table

Revision ID: 003_create_sync_logs
Revises: 002_create_content_tables
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_create_sync_logs"
down_revision: Union[str, None] = "002_create_content_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_memory_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("adapter", sa.String(length=64), nullable=False),
        sa.Column("checkpoint", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["content_memory_id"], ["content_memories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sync_logs_content_memory_id", "sync_logs", ["content_memory_id"]
    )
    op.create_index("ix_sync_logs_account_id", "sync_logs", ["account_id"])
    op.create_index("ix_sync_logs_synced_at", "sync_logs", ["synced_at"])


def downgrade() -> None:
    op.drop_index("ix_sync_logs_synced_at", table_name="sync_logs")
    op.drop_index("ix_sync_logs_account_id", table_name="sync_logs")
    op.drop_index("ix_sync_logs_content_memory_id", table_name="sync_logs")
    op.drop_table("sync_logs")
