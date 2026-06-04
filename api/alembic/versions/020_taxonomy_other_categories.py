"""Add domain/persona 'other' category seeds aligned with classification taxonomy.

Revision ID: 020_taxonomy_other_categories
Revises: 019_llm_budget
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "020_taxonomy_other_categories"
down_revision: str | None = "019_llm_budget"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Taxonomy enums in app.agents.classification.taxonomy are authoritative for the LLM.
# complaint_category 'other' was seeded in 002; domain/persona 'other' were missing.
TAXONOMY_OTHER_SEEDS: list[tuple[str, str, str, str]] = [
    ("other", "Other", "Uncategorized market domain", "domain"),
    ("other", "Other", "Uncategorized customer persona", "persona"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for code, label, description, kind in TAXONOMY_OTHER_SEEDS:
        bind.execute(
            sa.text(
                """
                INSERT INTO categories (code, label, description, kind)
                VALUES (:code, :label, :description, :kind)
                ON CONFLICT ON CONSTRAINT uq_categories_code_kind DO NOTHING
                """
            ),
            {"code": code, "label": label, "description": description, "kind": kind},
        )


def downgrade() -> None:
    for code, _, _, kind in TAXONOMY_OTHER_SEEDS:
        op.execute(
            sa.text("DELETE FROM categories WHERE code = :code AND kind = :kind").bindparams(
                code=code, kind=kind
            )
        )
