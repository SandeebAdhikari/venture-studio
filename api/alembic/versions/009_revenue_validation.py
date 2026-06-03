"""Add revenue validation tables.

Revision ID: 009_revenue_validation
Revises: 008_customer_research
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_revenue_validation"
down_revision: Union[str, None] = "008_customer_research"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "revenue_validations",
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
        sa.Column("willingness_to_pay_score", sa.Integer(), nullable=False),
        sa.Column("revenue_confidence_score", sa.Integer(), nullable=False),
        sa.Column(
            "pricing_recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "buyer_profiles",
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
            "validation_metadata",
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
        sa.CheckConstraint("version >= 1", name="ck_revenue_validations_version"),
        sa.CheckConstraint(
            "willingness_to_pay_score >= 0 AND willingness_to_pay_score <= 100",
            name="ck_revenue_validations_wtp_score",
        ),
        sa.CheckConstraint(
            "revenue_confidence_score >= 0 AND revenue_confidence_score <= 100",
            name="ck_revenue_validations_confidence_score",
        ),
    )
    op.create_index(
        "idx_revenue_validations_opportunity",
        "revenue_validations",
        ["opportunity_id", "created_at"],
    )
    op.create_index(
        "idx_revenue_validations_current",
        "revenue_validations",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index("idx_revenue_validations_status", "revenue_validations", ["status"])
    op.create_index("idx_revenue_validations_wtp", "revenue_validations", ["willingness_to_pay_score"])

    op.create_table(
        "revenue_validation_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("revenue_validation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("supports_conclusion", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("competitor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["revenue_validation_id"],
            ["revenue_validations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["competitor_profile_id"],
            ["competitor_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_revenue_validation_evidence_validation",
        "revenue_validation_evidence",
        ["revenue_validation_id"],
    )
    op.create_index(
        "idx_revenue_validation_evidence_complaint",
        "revenue_validation_evidence",
        ["complaint_id"],
    )

    for table in ("revenue_validations", "revenue_validation_evidence"):
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
        "DROP TRIGGER IF EXISTS trg_revenue_validation_evidence_updated_at "
        "ON revenue_validation_evidence"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_revenue_validations_updated_at ON revenue_validations"
    )
    op.drop_index(
        "idx_revenue_validation_evidence_complaint",
        table_name="revenue_validation_evidence",
    )
    op.drop_index(
        "idx_revenue_validation_evidence_validation",
        table_name="revenue_validation_evidence",
    )
    op.drop_table("revenue_validation_evidence")
    op.drop_index("idx_revenue_validations_wtp", table_name="revenue_validations")
    op.drop_index("idx_revenue_validations_status", table_name="revenue_validations")
    op.drop_index("idx_revenue_validations_current", table_name="revenue_validations")
    op.drop_index("idx_revenue_validations_opportunity", table_name="revenue_validations")
    op.drop_table("revenue_validations")
