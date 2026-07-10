"""create trend topics table

Revision ID: 006_create_trend_topics
Revises: 005_create_prediction_knowledge
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_create_trend_topics"
down_revision: Union[str, None] = "005_create_prediction_knowledge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trend_topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("heat_score", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("trend_date", sa.Date(), nullable=False),
        sa.Column("season", sa.String(length=64), nullable=True),
        sa.Column("festival", sa.String(length=128), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trend_topics_topic", "trend_topics", ["topic"])
    op.create_index("ix_trend_topics_category", "trend_topics", ["category"])
    op.create_index("ix_trend_topics_trend_date", "trend_topics", ["trend_date"])
    op.create_index("ix_trend_topics_season", "trend_topics", ["season"])
    op.create_index("ix_trend_topics_festival", "trend_topics", ["festival"])


def downgrade() -> None:
    op.drop_table("trend_topics")
