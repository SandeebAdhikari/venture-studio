"""Add scale provenance columns to human proxy evaluations.

Revision ID: 022_human_proxy_scale
Revises: 021_founder_signal_codes
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "022_human_proxy_scale"
down_revision: str | None = "021_founder_signal_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "human_proxy_evaluations",
        sa.Column(
            "scale_version",
            sa.String(length=32),
            nullable=False,
            server_default="legacy",
        ),
    )
    op.add_column(
        "human_proxy_evaluations",
        sa.Column(
            "scale_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("human_proxy_evaluations", "scale_metadata")
    op.drop_column("human_proxy_evaluations", "scale_version")
