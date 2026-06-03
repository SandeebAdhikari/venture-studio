"""Add LLM budget tracking columns and threshold alert history.

Revision ID: 019_llm_budget
Revises: 018_approval_workflow
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019_llm_budget"
down_revision: Union[str, None] = "018_approval_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_calls",
        sa.Column("estimated_cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
    )

    op.create_table(
        "llm_budget_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("budget_date", sa.Date(), nullable=False),
        sa.Column("threshold_pct", sa.Integer(), nullable=False),
        sa.Column("spent_usd", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("budget_usd", sa.Numeric(precision=10, scale=6), nullable=False),
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
        sa.UniqueConstraint("budget_date", "threshold_pct", name="uq_llm_budget_alerts_day_threshold"),
    )
    op.create_index(
        "idx_llm_budget_alerts_date",
        "llm_budget_alerts",
        ["budget_date"],
        unique=False,
    )

    op.execute(
        """
        CREATE TRIGGER trg_llm_budget_alerts_updated_at
        BEFORE UPDATE ON llm_budget_alerts
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_llm_budget_alerts_updated_at ON llm_budget_alerts")
    op.drop_index("idx_llm_budget_alerts_date", table_name="llm_budget_alerts")
    op.drop_table("llm_budget_alerts")
    op.drop_column("llm_calls", "estimated_cost_usd")
