"""Add customer research tables.

Revision ID: 008_customer_research
Revises: 007_competitor_intelligence
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_customer_research"
down_revision: Union[str, None] = "007_competitor_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_research",
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
        sa.Column("pain_score", sa.Integer(), nullable=False),
        sa.Column("urgency_score", sa.Integer(), nullable=False),
        sa.Column("frequency_score", sa.Integer(), nullable=False),
        sa.Column("customer_sentiment", sa.String(length=20), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("cares_verdict", sa.String(length=20), nullable=False),
        sa.Column(
            "representative_complaints",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column(
            "validation_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.CheckConstraint("version >= 1", name="ck_customer_research_version"),
        sa.CheckConstraint(
            "pain_score >= 0 AND pain_score <= 100",
            name="ck_customer_research_pain_score",
        ),
        sa.CheckConstraint(
            "urgency_score >= 0 AND urgency_score <= 100",
            name="ck_customer_research_urgency_score",
        ),
        sa.CheckConstraint(
            "frequency_score >= 0 AND frequency_score <= 100",
            name="ck_customer_research_frequency_score",
        ),
        sa.CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="ck_customer_research_sentiment_score",
        ),
    )
    op.create_index(
        "idx_customer_research_opportunity",
        "customer_research",
        ["opportunity_id", "created_at"],
    )
    op.create_index(
        "idx_customer_research_current",
        "customer_research",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index("idx_customer_research_status", "customer_research", ["status"])
    op.create_index("idx_customer_research_pain_score", "customer_research", ["pain_score"])

    op.create_table(
        "customer_research_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("customer_research_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(length=30), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("supports_conclusion", sa.String(length=30), nullable=False),
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
            ["customer_research_id"],
            ["customer_research.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_customer_research_evidence_research",
        "customer_research_evidence",
        ["customer_research_id"],
    )
    op.create_index(
        "idx_customer_research_evidence_complaint",
        "customer_research_evidence",
        ["complaint_id"],
    )

    for table in ("customer_research", "customer_research_evidence"):
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
        "DROP TRIGGER IF EXISTS trg_customer_research_evidence_updated_at "
        "ON customer_research_evidence"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_research_updated_at ON customer_research"
    )
    op.drop_index("idx_customer_research_evidence_complaint", table_name="customer_research_evidence")
    op.drop_index("idx_customer_research_evidence_research", table_name="customer_research_evidence")
    op.drop_table("customer_research_evidence")
    op.drop_index("idx_customer_research_pain_score", table_name="customer_research")
    op.drop_index("idx_customer_research_status", table_name="customer_research")
    op.drop_index("idx_customer_research_current", table_name="customer_research")
    op.drop_index("idx_customer_research_opportunity", table_name="customer_research")
    op.drop_table("customer_research")
