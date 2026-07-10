"""create prediction and knowledge evolution tables

Revision ID: 005_create_prediction_knowledge
Revises: 004_create_learning_tables
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_create_prediction_knowledge"
down_revision: Union[str, None] = "004_create_learning_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("predict_threshold", sa.Float(), nullable=True),
    )

    op.create_table(
        "prediction_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("predict_view", sa.Integer(), nullable=False),
        sa.Column("actual_view", sa.Integer(), nullable=True),
        sa.Column("predict_finish_rate", sa.Float(), nullable=False),
        sa.Column("actual_finish_rate", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=True),
        sa.Column("predict_level", sa.Integer(), nullable=False),
        sa.Column("reason", sa.JSON(), nullable=False),
        sa.Column("dna_tags_snapshot", sa.JSON(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("threshold_used", sa.Float(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["video_id"], ["content_memories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prediction_histories_account_id",
        "prediction_histories",
        ["account_id"],
    )
    op.create_index(
        "ix_prediction_histories_video_id",
        "prediction_histories",
        ["video_id"],
    )

    op.create_table(
        "knowledge_evolutions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_type", sa.String(length=16), nullable=False),
        sa.Column("dimension_scores", sa.JSON(), nullable=False),
        sa.Column("analysis_text", sa.Text(), nullable=False),
        sa.Column("views_at_analysis", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["video_id"], ["content_memories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )
    op.create_index(
        "ix_knowledge_evolutions_account_id",
        "knowledge_evolutions",
        ["account_id"],
    )
    op.create_index(
        "ix_knowledge_evolutions_video_id",
        "knowledge_evolutions",
        ["video_id"],
    )
    op.create_index(
        "ix_knowledge_evolutions_knowledge_type",
        "knowledge_evolutions",
        ["knowledge_type"],
    )


def downgrade() -> None:
    op.drop_table("knowledge_evolutions")
    op.drop_table("prediction_histories")
    op.drop_column("accounts", "predict_threshold")
