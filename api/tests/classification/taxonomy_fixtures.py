"""Ensure taxonomy rows required by classification tests exist."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_OTHER_SEEDS = (
    ("other", "Other", "Uncategorized market domain", "domain"),
    ("other", "Other", "Uncategorized customer persona", "persona"),
)


async def ensure_other_category_seeds(session: AsyncSession) -> None:
    for code, label, description, kind in _OTHER_SEEDS:
        await session.execute(
            text(
                """
                INSERT INTO categories (code, label, description, kind)
                VALUES (:code, :label, :description, :kind)
                ON CONFLICT ON CONSTRAINT uq_categories_code_kind DO NOTHING
                """
            ),
            {"code": code, "label": label, "description": description, "kind": kind},
        )
    await session.flush()
