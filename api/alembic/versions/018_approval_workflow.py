"""Add founder approval workflow tables.

Revision ID: 018_approval_workflow
Revises: 017_scheduler
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "018_approval_workflow"
down_revision: str | None = "017_scheduler"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("subject_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("executive_ranking_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "audit_trail",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(executive_ranking_run_id IS NOT NULL) OR (report_id IS NOT NULL)",
            name="ck_approval_requests_subject",
        ),
    )
    op.create_index("idx_approval_requests_status", "approval_requests", ["status"])
    op.create_index("idx_approval_requests_subject_type", "approval_requests", ["subject_type"])
    op.create_index(
        "idx_approval_requests_ranking_run",
        "approval_requests",
        ["executive_ranking_run_id"],
    )
    op.create_index("idx_approval_requests_report", "approval_requests", ["report_id"])

    op.create_table(
        "approval_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_type", sa.String(length=30), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=100), server_default="founder", nullable=False),
        sa.Column(
            "metadata",
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
            ["approval_request_id"],
            ["approval_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_approval_decisions_request",
        "approval_decisions",
        ["approval_request_id"],
    )
    op.create_index(
        "idx_approval_decisions_created",
        "approval_decisions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_approval_decisions_created", table_name="approval_decisions")
    op.drop_index("idx_approval_decisions_request", table_name="approval_decisions")
    op.drop_table("approval_decisions")
    op.drop_index("idx_approval_requests_report", table_name="approval_requests")
    op.drop_index("idx_approval_requests_ranking_run", table_name="approval_requests")
    op.drop_index("idx_approval_requests_subject_type", table_name="approval_requests")
    op.drop_index("idx_approval_requests_status", table_name="approval_requests")
    op.drop_table("approval_requests")
