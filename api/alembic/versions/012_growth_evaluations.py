"""Add growth evaluation tables.

Revision ID: 012_growth_evaluations
Revises: 011_gtm_plans
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "012_growth_evaluations"
down_revision: str | None = "011_gtm_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "growth_evaluations",
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
        sa.Column("growth_score", sa.Integer(), nullable=False),
        sa.Column("scalability_score", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column(
            "seo_potential",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "referral_potential",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "partnership_opportunities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "paid_acquisition_potential",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "market_expansion_opportunities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "growth_roadmap",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column(
            "evaluation_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("llm_model", sa.String(length=50), nullable=False),
        sa.Column(
            "evaluation_metadata",
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
        sa.CheckConstraint("version >= 1", name="ck_growth_evaluations_version"),
        sa.CheckConstraint(
            "growth_score >= 0 AND growth_score <= 100",
            name="ck_growth_evaluations_growth_score",
        ),
        sa.CheckConstraint(
            "scalability_score >= 0 AND scalability_score <= 100",
            name="ck_growth_evaluations_scalability_score",
        ),
        sa.CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_growth_evaluations_risk_score",
        ),
    )
    op.create_index(
        "idx_growth_evaluations_opportunity",
        "growth_evaluations",
        ["opportunity_id", "created_at"],
    )
    op.create_index(
        "idx_growth_evaluations_current",
        "growth_evaluations",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index("idx_growth_evaluations_status", "growth_evaluations", ["status"])
    op.create_index(
        "idx_growth_evaluations_growth_score",
        "growth_evaluations",
        ["growth_score"],
    )
    op.create_index(
        "idx_growth_evaluations_scalability_score",
        "growth_evaluations",
        ["scalability_score"],
    )

    op.create_table(
        "growth_evaluation_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("growth_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("supports_conclusion", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["growth_evaluation_id"],
            ["growth_evaluations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_growth_evaluation_evidence_evaluation",
        "growth_evaluation_evidence",
        ["growth_evaluation_id"],
    )
    op.create_index(
        "idx_growth_evaluation_evidence_complaint",
        "growth_evaluation_evidence",
        ["complaint_id"],
    )

    for table in ("growth_evaluations", "growth_evaluation_evidence"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_growth_evaluation_evidence_updated_at "
        "ON growth_evaluation_evidence"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_growth_evaluations_updated_at ON growth_evaluations")
    op.drop_index(
        "idx_growth_evaluation_evidence_complaint",
        table_name="growth_evaluation_evidence",
    )
    op.drop_index(
        "idx_growth_evaluation_evidence_evaluation",
        table_name="growth_evaluation_evidence",
    )
    op.drop_table("growth_evaluation_evidence")
    op.drop_index(
        "idx_growth_evaluations_scalability_score",
        table_name="growth_evaluations",
    )
    op.drop_index("idx_growth_evaluations_growth_score", table_name="growth_evaluations")
    op.drop_index("idx_growth_evaluations_status", table_name="growth_evaluations")
    op.drop_index("idx_growth_evaluations_current", table_name="growth_evaluations")
    op.drop_index("idx_growth_evaluations_opportunity", table_name="growth_evaluations")
    op.drop_table("growth_evaluations")
