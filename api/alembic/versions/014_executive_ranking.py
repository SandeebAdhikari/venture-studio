"""Add executive ranking runs and entries.

Revision ID: 014_executive_ranking
Revises: 013_human_proxy
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "014_executive_ranking"
down_revision: str | None = "013_human_proxy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "executive_ranking_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="completed", nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("founder_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("top_n", sa.Integer(), server_default="5", nullable=False),
        sa.Column("opportunity_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ranked_opportunity_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ranking_engine", sa.String(length=50), nullable=False),
        sa.Column(
            "ranking_metadata",
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
        sa.ForeignKeyConstraint(
            ["founder_profile_id"],
            ["founder_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("version >= 1", name="ck_executive_ranking_runs_version"),
        sa.CheckConstraint("top_n >= 1", name="ck_executive_ranking_runs_top_n"),
    )
    op.create_index(
        "idx_executive_ranking_runs_current",
        "executive_ranking_runs",
        ["is_current"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index("idx_executive_ranking_runs_version", "executive_ranking_runs", ["version"])
    op.create_index("idx_executive_ranking_runs_status", "executive_ranking_runs", ["status"])

    op.create_table(
        "executive_ranking_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("executive_ranking_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("final_opportunity_score", sa.Integer(), nullable=False),
        sa.Column("pain_score", sa.Integer(), nullable=True),
        sa.Column("market_score", sa.Integer(), nullable=True),
        sa.Column("revenue_score", sa.Integer(), nullable=True),
        sa.Column("competition_score", sa.Integer(), nullable=True),
        sa.Column("growth_score", sa.Integer(), nullable=True),
        sa.Column("founder_fit_score", sa.Integer(), nullable=True),
        sa.Column("agent_coverage_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "is_top_opportunity", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "source_references",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "ranking_details",
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
        sa.ForeignKeyConstraint(
            ["executive_ranking_run_id"],
            ["executive_ranking_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rank >= 1", name="ck_executive_ranking_entries_rank"),
        sa.CheckConstraint(
            "final_opportunity_score >= 0 AND final_opportunity_score <= 100",
            name="ck_executive_ranking_entries_final_score",
        ),
        sa.CheckConstraint(
            "pain_score IS NULL OR (pain_score >= 0 AND pain_score <= 100)",
            name="ck_executive_ranking_entries_pain",
        ),
        sa.CheckConstraint(
            "market_score IS NULL OR (market_score >= 0 AND market_score <= 100)",
            name="ck_executive_ranking_entries_market",
        ),
        sa.CheckConstraint(
            "revenue_score IS NULL OR (revenue_score >= 0 AND revenue_score <= 100)",
            name="ck_executive_ranking_entries_revenue",
        ),
        sa.CheckConstraint(
            "competition_score IS NULL OR (competition_score >= 0 AND competition_score <= 100)",
            name="ck_executive_ranking_entries_competition",
        ),
        sa.CheckConstraint(
            "growth_score IS NULL OR (growth_score >= 0 AND growth_score <= 100)",
            name="ck_executive_ranking_entries_growth",
        ),
        sa.CheckConstraint(
            "founder_fit_score IS NULL OR (founder_fit_score >= 0 AND founder_fit_score <= 100)",
            name="ck_executive_ranking_entries_founder_fit",
        ),
    )
    op.create_index(
        "idx_executive_ranking_entries_run",
        "executive_ranking_entries",
        ["executive_ranking_run_id", "rank"],
    )
    op.create_index(
        "idx_executive_ranking_entries_opportunity",
        "executive_ranking_entries",
        ["opportunity_id", "created_at"],
    )
    op.create_index(
        "idx_executive_ranking_entries_top",
        "executive_ranking_entries",
        ["executive_ranking_run_id", "is_top_opportunity"],
    )


def downgrade() -> None:
    op.drop_index("idx_executive_ranking_entries_top", table_name="executive_ranking_entries")
    op.drop_index(
        "idx_executive_ranking_entries_opportunity", table_name="executive_ranking_entries"
    )
    op.drop_index("idx_executive_ranking_entries_run", table_name="executive_ranking_entries")
    op.drop_table("executive_ranking_entries")
    op.drop_index("idx_executive_ranking_runs_status", table_name="executive_ranking_runs")
    op.drop_index("idx_executive_ranking_runs_version", table_name="executive_ranking_runs")
    op.drop_index("idx_executive_ranking_runs_current", table_name="executive_ranking_runs")
    op.drop_table("executive_ranking_runs")
