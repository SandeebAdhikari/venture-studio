"""Tests that taxonomy codes resolve to seeded category rows."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.category import Category
from app.repositories import get_repositories
from tests.classification.taxonomy_fixtures import ensure_other_category_seeds


@pytest.fixture(autouse=True)
async def _taxonomy_other_seeds(db_session: AsyncSession) -> None:
    await ensure_other_category_seeds(db_session)


@pytest.mark.asyncio
async def test_resolve_other_persona_and_domain(db_session: AsyncSession) -> None:
    repos = get_repositories(db_session)

    for kind in ("domain", "persona"):
        row = await db_session.scalar(
            select(Category).where(Category.code == "other", Category.kind == kind)
        )
        assert row is not None, f"Expected categories row for other/{kind}"

    resolved = await repos.complaints.resolve_category_ids(
        category_code="other",
        domain_code="other",
        persona_code="other",
    )
    assert resolved is not None
    category, domain, persona = resolved
    assert category.code == "other"
    assert domain.code == "other"
    assert persona.code == "other"
