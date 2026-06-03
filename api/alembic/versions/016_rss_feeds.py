"""Add RSS feed configuration table.

Revision ID: 016_rss_feeds
Revises: 015_pipeline
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "016_rss_feeds"
down_revision: str | None = "015_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rss_feeds",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("polling_interval_sec", sa.Integer(), server_default="3600", nullable=False),
        sa.Column("entry_limit", sa.Integer(), server_default="30", nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_url"),
        sa.UniqueConstraint("source_id"),
        sa.CheckConstraint("polling_interval_sec >= 60", name="ck_rss_feeds_polling_interval"),
        sa.CheckConstraint("entry_limit >= 1", name="ck_rss_feeds_entry_limit"),
    )
    op.create_index("idx_rss_feeds_enabled", "rss_feeds", ["enabled"])
    op.create_index("idx_rss_feeds_category", "rss_feeds", ["category"])
    op.create_index("idx_rss_feeds_last_polled", "rss_feeds", ["last_polled_at"])


def downgrade() -> None:
    op.drop_index("idx_rss_feeds_last_polled", table_name="rss_feeds")
    op.drop_index("idx_rss_feeds_category", table_name="rss_feeds")
    op.drop_index("idx_rss_feeds_enabled", table_name="rss_feeds")
    op.drop_table("rss_feeds")
