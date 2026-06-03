"""Add founder profiles and human proxy evaluation tables.

Revision ID: 013_human_proxy
Revises: 012_growth_evaluations
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_human_proxy"
down_revision: Union[str, None] = "012_growth_evaluations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "founder_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "profile_metadata",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_founder_profiles_default",
        "founder_profiles",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )
    op.create_index("idx_founder_profiles_active", "founder_profiles", ["is_active"])

    op.execute(
        """
        INSERT INTO founder_profiles (
            name,
            description,
            skills,
            constraints,
            is_default,
            is_active,
            profile_metadata
        ) VALUES (
            'Default Solo Technical Founder',
            'Solo founder with a full-stack web and data stack and limited budget and time.',
            '["Next.js", "TypeScript", "Python", "PostgreSQL"]'::jsonb,
            '{"team_size": "solo", "budget": "limited", "time": "limited"}'::jsonb,
            true,
            true,
            '{"source": "system_default"}'::jsonb
        )
        """
    )

    op.create_table(
        "human_proxy_evaluations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("founder_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="completed", nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("founder_fit_score", sa.Integer(), nullable=False),
        sa.Column("feasibility_score", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column(
            "founder_fit_analysis",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "implementation_feasibility",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "learning_curve",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "execution_complexity",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "capital_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
            "proxy_metadata",
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
        sa.ForeignKeyConstraint(["founder_profile_id"], ["founder_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("version >= 1", name="ck_human_proxy_evaluations_version"),
        sa.CheckConstraint(
            "founder_fit_score >= 0 AND founder_fit_score <= 100",
            name="ck_human_proxy_evaluations_founder_fit",
        ),
        sa.CheckConstraint(
            "feasibility_score >= 0 AND feasibility_score <= 100",
            name="ck_human_proxy_evaluations_feasibility",
        ),
    )
    op.create_index(
        "idx_human_proxy_evaluations_opportunity",
        "human_proxy_evaluations",
        ["opportunity_id", "created_at"],
    )
    op.create_index(
        "idx_human_proxy_evaluations_current",
        "human_proxy_evaluations",
        ["opportunity_id", "founder_profile_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index("idx_human_proxy_evaluations_status", "human_proxy_evaluations", ["status"])
    op.create_index(
        "idx_human_proxy_evaluations_founder_fit",
        "human_proxy_evaluations",
        ["founder_fit_score"],
    )
    op.create_index(
        "idx_human_proxy_evaluations_feasibility",
        "human_proxy_evaluations",
        ["feasibility_score"],
    )
    op.create_index(
        "idx_human_proxy_evaluations_profile",
        "human_proxy_evaluations",
        ["founder_profile_id"],
    )

    op.create_table(
        "human_proxy_evaluation_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("human_proxy_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            ["human_proxy_evaluation_id"],
            ["human_proxy_evaluations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_human_proxy_evaluation_evidence_evaluation",
        "human_proxy_evaluation_evidence",
        ["human_proxy_evaluation_id"],
    )
    op.create_index(
        "idx_human_proxy_evaluation_evidence_complaint",
        "human_proxy_evaluation_evidence",
        ["complaint_id"],
    )

    for table in ("founder_profiles", "human_proxy_evaluations", "human_proxy_evaluation_evidence"):
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
        "DROP TRIGGER IF EXISTS trg_human_proxy_evaluation_evidence_updated_at "
        "ON human_proxy_evaluation_evidence"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_human_proxy_evaluations_updated_at ON human_proxy_evaluations"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_founder_profiles_updated_at ON founder_profiles")
    op.drop_index(
        "idx_human_proxy_evaluation_evidence_complaint",
        table_name="human_proxy_evaluation_evidence",
    )
    op.drop_index(
        "idx_human_proxy_evaluation_evidence_evaluation",
        table_name="human_proxy_evaluation_evidence",
    )
    op.drop_table("human_proxy_evaluation_evidence")
    op.drop_index("idx_human_proxy_evaluations_profile", table_name="human_proxy_evaluations")
    op.drop_index("idx_human_proxy_evaluations_feasibility", table_name="human_proxy_evaluations")
    op.drop_index("idx_human_proxy_evaluations_founder_fit", table_name="human_proxy_evaluations")
    op.drop_index("idx_human_proxy_evaluations_status", table_name="human_proxy_evaluations")
    op.drop_index("idx_human_proxy_evaluations_current", table_name="human_proxy_evaluations")
    op.drop_index("idx_human_proxy_evaluations_opportunity", table_name="human_proxy_evaluations")
    op.drop_table("human_proxy_evaluations")
    op.drop_index("idx_founder_profiles_active", table_name="founder_profiles")
    op.drop_index("idx_founder_profiles_default", table_name="founder_profiles")
    op.drop_table("founder_profiles")
