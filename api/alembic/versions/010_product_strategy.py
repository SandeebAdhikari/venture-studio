"""Add product strategy tables.

Revision ID: 010_product_strategy
Revises: 009_revenue_validation
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_product_strategy"
down_revision: Union[str, None] = "009_revenue_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_strategies",
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
        sa.Column("mvp_definition", sa.Text(), nullable=False),
        sa.Column(
            "core_features",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "feature_priorities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "development_phases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "estimated_timeline",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "technical_risks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "roadmap",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column(
            "planning_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("llm_model", sa.String(length=50), nullable=False),
        sa.Column(
            "strategy_metadata",
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
        sa.CheckConstraint("version >= 1", name="ck_product_strategies_version"),
    )
    op.create_index(
        "idx_product_strategies_opportunity",
        "product_strategies",
        ["opportunity_id", "created_at"],
    )
    op.create_index(
        "idx_product_strategies_current",
        "product_strategies",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index("idx_product_strategies_status", "product_strategies", ["status"])

    op.create_table(
        "product_strategy_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("product_strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            ["product_strategy_id"],
            ["product_strategies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_product_strategy_evidence_strategy",
        "product_strategy_evidence",
        ["product_strategy_id"],
    )
    op.create_index(
        "idx_product_strategy_evidence_complaint",
        "product_strategy_evidence",
        ["complaint_id"],
    )

    for table in ("product_strategies", "product_strategy_evidence"):
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
        "DROP TRIGGER IF EXISTS trg_product_strategy_evidence_updated_at "
        "ON product_strategy_evidence"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_product_strategies_updated_at ON product_strategies"
    )
    op.drop_index(
        "idx_product_strategy_evidence_complaint",
        table_name="product_strategy_evidence",
    )
    op.drop_index(
        "idx_product_strategy_evidence_strategy",
        table_name="product_strategy_evidence",
    )
    op.drop_table("product_strategy_evidence")
    op.drop_index("idx_product_strategies_status", table_name="product_strategies")
    op.drop_index("idx_product_strategies_current", table_name="product_strategies")
    op.drop_index("idx_product_strategies_opportunity", table_name="product_strategies")
    op.drop_table("product_strategies")
