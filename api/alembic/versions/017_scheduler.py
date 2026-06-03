"""Add scheduler job configuration and run history.

Revision ID: 017_scheduler
Revises: 016_rss_feeds
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "017_scheduler"
down_revision: str | None = "016_rss_feeds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduler_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schedule_hour", sa.Integer(), nullable=False),
        sa.Column("schedule_minute", sa.Integer(), server_default="0", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.UniqueConstraint("job_name"),
        sa.CheckConstraint(
            "schedule_hour >= 0 AND schedule_hour <= 23", name="ck_scheduler_jobs_hour"
        ),
        sa.CheckConstraint(
            "schedule_minute >= 0 AND schedule_minute <= 59",
            name="ck_scheduler_jobs_minute",
        ),
    )
    op.create_index("idx_scheduler_jobs_enabled", "scheduler_jobs", ["enabled"])

    op.create_table(
        "scheduler_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_name", sa.String(length=50), nullable=False),
        sa.Column("trigger", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "arq_job_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["job_name"], ["scheduler_jobs.job_name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scheduler_runs_job_name", "scheduler_runs", ["job_name"])
    op.create_index("idx_scheduler_runs_status", "scheduler_runs", ["status"])
    op.create_index("idx_scheduler_runs_started_at", "scheduler_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("idx_scheduler_runs_started_at", table_name="scheduler_runs")
    op.drop_index("idx_scheduler_runs_status", table_name="scheduler_runs")
    op.drop_index("idx_scheduler_runs_job_name", table_name="scheduler_runs")
    op.drop_table("scheduler_runs")
    op.drop_index("idx_scheduler_jobs_enabled", table_name="scheduler_jobs")
    op.drop_table("scheduler_jobs")
