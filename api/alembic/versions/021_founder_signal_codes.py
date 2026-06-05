"""Add founder signal enum columns to complaints.

Revision ID: 021_founder_signal_codes
Revises: 020_taxonomy_other_categories
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "021_founder_signal_codes"
down_revision: str | None = "020_taxonomy_other_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("complaints", sa.Column("business_function_code", sa.String(64), nullable=True))
    op.add_column("complaints", sa.Column("jtbd_code", sa.String(64), nullable=True))
    op.add_column("complaints", sa.Column("consequence_code", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("complaints", "consequence_code")
    op.drop_column("complaints", "jtbd_code")
    op.drop_column("complaints", "business_function_code")
