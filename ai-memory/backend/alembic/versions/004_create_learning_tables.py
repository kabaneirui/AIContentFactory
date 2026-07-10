"""create brain learning and account profile tables

Revision ID: 004_create_learning_tables
Revises: 003_create_sync_logs
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_create_learning_tables"
down_revision: Union[str, None] = "003_create_sync_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brain_learnings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("learning_date", sa.Date(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("strength", sa.Text(), nullable=False),
        sa.Column("weakness", sa.Text(), nullable=False),
        sa.Column("trend", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("optimization", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=True),
        sa.Column("stats_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_brain_learnings_account_id",
        "brain_learnings",
        ["account_id"],
    )
    op.create_index(
        "ix_brain_learnings_learning_date",
        "brain_learnings",
        ["learning_date"],
    )

    op.create_table(
        "account_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=True),
        sa.Column("account_type", sa.String(length=128), nullable=True),
        sa.Column("best_category", sa.String(length=128), nullable=True),
        sa.Column("best_scene", sa.String(length=128), nullable=True),
        sa.Column("best_duration", sa.String(length=64), nullable=True),
        sa.Column("best_publish_time", sa.String(length=16), nullable=True),
        sa.Column("best_cta", sa.String(length=64), nullable=True),
        sa.Column("best_hook", sa.String(length=128), nullable=True),
        sa.Column("best_knowledge_source", sa.String(length=255), nullable=True),
        sa.Column("locked_fields", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
    )
    op.create_index(
        "ix_account_profiles_account_id",
        "account_profiles",
        ["account_id"],
    )


def downgrade() -> None:
    op.drop_table("account_profiles")
    op.drop_table("brain_learnings")
