"""create content memory and performance tables

Revision ID: 002_create_content_tables
Revises: 001_create_accounts
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_create_content_tables"
down_revision: Union[str, None] = "001_create_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_memories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("platform_video_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("script", sa.Text(), nullable=True),
        sa.Column("hook", sa.String(length=512), nullable=True),
        sa.Column("template", sa.String(length=128), nullable=True),
        sa.Column("knowledge_source", sa.String(length=255), nullable=True),
        sa.Column("prompt", sa.String(length=128), nullable=True),
        sa.Column("scene_style", sa.String(length=128), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("cta", sa.String(length=255), nullable=True),
        sa.Column("publish_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("season", sa.String(length=64), nullable=True),
        sa.Column("festival", sa.String(length=128), nullable=True),
        sa.Column("weather", sa.String(length=64), nullable=True),
        sa.Column("keyword", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("dna_tags", sa.JSON(), nullable=True),
        sa.Column(
            "lifecycle_status",
            sa.String(length=32),
            nullable=False,
            server_default="created",
        ),
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
        "ix_content_memories_account_id", "content_memories", ["account_id"]
    )
    op.create_index(
        "ix_content_memories_lifecycle_status",
        "content_memories",
        ["lifecycle_status"],
    )

    op.create_table(
        "content_performances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_memory_id", sa.Integer(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("rate_3s", sa.Float(), nullable=True),
        sa.Column("finish_rate", sa.Float(), nullable=True),
        sa.Column("average_watch", sa.Float(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("collects", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forwards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fans_increase", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach_level", sa.String(length=64), nullable=True),
        sa.Column("recommend_rate", sa.Float(), nullable=True),
        sa.Column("engagement_rate", sa.Float(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_memory_id"], ["content_memories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_memory_id"),
    )
    op.create_index(
        "ix_content_performances_content_memory_id",
        "content_performances",
        ["content_memory_id"],
    )

    op.create_table(
        "performance_sync_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_memory_id", sa.Integer(), nullable=False),
        sa.Column("checkpoint", sa.String(length=8), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_memory_id"], ["content_memories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_performance_sync_tasks_content_memory_id",
        "performance_sync_tasks",
        ["content_memory_id"],
    )
    op.create_index(
        "ix_performance_sync_tasks_due_at",
        "performance_sync_tasks",
        ["due_at"],
    )


def downgrade() -> None:
    op.drop_table("performance_sync_tasks")
    op.drop_table("content_performances")
    op.drop_table("content_memories")
