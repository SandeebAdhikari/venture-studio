"""Add market_briefs table for opportunity market intelligence.

Revision ID: 006_market_briefs
Revises: 005_opportunity_score_dimensions
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006_market_briefs"
down_revision: str | None = "005_opportunity_score_dimensions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_briefs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="completed", nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("market_size_usd", sa.Float(), nullable=True),
        sa.Column("tam_usd", sa.Float(), nullable=True),
        sa.Column("sam_usd", sa.Float(), nullable=True),
        sa.Column("industry_growth_rate_pct", sa.Float(), nullable=True),
        sa.Column(
            "customer_segments",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "industry_trends",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "supporting_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(length=50), nullable=False),
        sa.Column(
            "research_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
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
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("version >= 1", name="ck_market_briefs_version"),
        sa.CheckConstraint(
            "industry_growth_rate_pct IS NULL OR "
            "(industry_growth_rate_pct >= -50 AND industry_growth_rate_pct <= 100)",
            name="ck_market_briefs_growth_rate",
        ),
        sa.CheckConstraint(
            "market_size_usd IS NULL OR market_size_usd >= 0",
            name="ck_market_briefs_market_size",
        ),
        sa.CheckConstraint("tam_usd IS NULL OR tam_usd >= 0", name="ck_market_briefs_tam"),
        sa.CheckConstraint("sam_usd IS NULL OR sam_usd >= 0", name="ck_market_briefs_sam"),
    )
    op.create_index(
        "idx_market_briefs_opportunity", "market_briefs", ["opportunity_id", "created_at"]
    )
    op.create_index(
        "idx_market_briefs_current",
        "market_briefs",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index("idx_market_briefs_status", "market_briefs", ["status"])

    op.execute(
        """
        CREATE TRIGGER trg_market_briefs_updated_at
        BEFORE UPDATE ON market_briefs
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_market_briefs_updated_at ON market_briefs")
    op.drop_index("idx_market_briefs_status", table_name="market_briefs")
    op.drop_index("idx_market_briefs_current", table_name="market_briefs")
    op.drop_index("idx_market_briefs_opportunity", table_name="market_briefs")
    op.drop_table("market_briefs")
