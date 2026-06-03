"""Add llm_calls table for agent evaluation logging.

Revision ID: 004_llm_calls
Revises: 003_signal_content_hash
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004_llm_calls"
down_revision: str | None = "003_signal_content_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_calls",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("graph_name", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="success"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "eval_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
    op.create_index("idx_llm_calls_entity", "llm_calls", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_llm_calls_created", "llm_calls", ["created_at"], unique=False)
    op.create_index(
        "idx_llm_calls_graph_status", "llm_calls", ["graph_name", "status"], unique=False
    )

    for table in ("llm_calls",):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_llm_calls_updated_at ON llm_calls")
    op.drop_index("idx_llm_calls_graph_status", table_name="llm_calls")
    op.drop_index("idx_llm_calls_created", table_name="llm_calls")
    op.drop_index("idx_llm_calls_entity", table_name="llm_calls")
    op.drop_table("llm_calls")
