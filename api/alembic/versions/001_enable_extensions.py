"""Initial infrastructure extensions.

Enables PostgreSQL extensions required by the AI Venture Studio schema.
Business tables are added in subsequent migrations.

Revision ID: 001_extensions
Revises:
Create Date: 2026-06-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "001_extensions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
