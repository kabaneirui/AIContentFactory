"""create prompt versions table

Revision ID: 007_create_prompt_versions
Revises: 006_create_trend_topics
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_create_prompt_versions"
down_revision: Union[str, None] = "006_create_trend_topics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "auto_evolve",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("prompt_content", sa.Text(), nullable=False),
        sa.Column("change_log", sa.Text(), nullable=True),
        sa.Column("video_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("avg_view", sa.Float(), server_default="0", nullable=False),
        sa.Column("avg_finish_rate", sa.Float(), server_default="0", nullable=False),
        sa.Column("recommend_score", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
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
        sa.UniqueConstraint("account_id", "version", name="uq_prompt_versions_account_version"),
    )
    op.create_index(
        "ix_prompt_versions_account_id",
        "prompt_versions",
        ["account_id"],
    )


def downgrade() -> None:
    op.drop_table("prompt_versions")
    op.drop_column("accounts", "auto_evolve")
