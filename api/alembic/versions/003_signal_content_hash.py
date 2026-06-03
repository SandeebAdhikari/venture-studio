"""Add content_hash to signals for collection deduplication.

Revision ID: 003_signal_content_hash
Revises: 002_core_persistence
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_signal_content_hash"
down_revision: Union[str, None] = "002_core_persistence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.create_index(
        "idx_signals_source_content_hash",
        "signals",
        ["source_id", "content_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_signals_source_content_hash", table_name="signals")
    op.drop_column("signals", "content_hash")
