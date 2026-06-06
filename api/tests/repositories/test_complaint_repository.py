"""Integration tests for complaint repository persistence."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CategoryKind, SourceType
from app.db.models.category import Category
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from sqlalchemy import select


@pytest.fixture
async def taxonomy_ids(db_session: AsyncSession) -> tuple:
    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "pricing",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "fintech",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "founder",
        )
    )
    assert category is not None and domain is not None and persona is not None
    return category.id, domain.id, persona.id


async def _pending_signal(db_session: AsyncSession) -> Signal:
    source = Source(
        name=f"complaint-repo-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url=f"https://example.com/posts/{uuid4()}",
        title="Stripe chargeback pain",
        body="Why are we getting fscked sideways by Stripe, BoA & the customer ?",
        processing_status="pending",
    )
    db_session.add(signal)
    await db_session.flush()
    return signal


@pytest.mark.asyncio
async def test_create_persists_founder_signals_and_reload_preserves_values(
    db_session: AsyncSession,
    taxonomy_ids: tuple,
) -> None:
    category_id, domain_id, persona_id = taxonomy_ids
    signal = await _pending_signal(db_session)
    repos = get_repositories(db_session)

    created = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category_id,
            domain_id=domain_id,
            persona_id=persona_id,
            summary="Frustration over Stripe chargeback fees and dispute handling.",
            verbatim_quote="Why are we getting fscked sideways by Stripe, BoA & the customer ?",
            severity=4,
            product_mentions=["Stripe"],
            llm_model="mock-classifier",
            llm_confidence=0.91,
            business_function_code="fraud_prevention",
            jtbd_code="prevent_fraud",
            consequence_code="margin_erosion",
        )
    )

    assert created.business_function_code == "fraud_prevention"
    assert created.jtbd_code == "prevent_fraud"
    assert created.consequence_code == "margin_erosion"

    complaint_id = created.id
    db_session.expire_all()
    reloaded = await repos.complaints.get_by_id(complaint_id)
    assert reloaded is not None
    assert reloaded.business_function_code == "fraud_prevention"
    assert reloaded.jtbd_code == "prevent_fraud"
    assert reloaded.consequence_code == "margin_erosion"


@pytest.mark.asyncio
async def test_create_without_founder_signals_remains_null(
    db_session: AsyncSession,
    taxonomy_ids: tuple,
) -> None:
    category_id, domain_id, persona_id = taxonomy_ids
    signal = await _pending_signal(db_session)
    repos = get_repositories(db_session)

    created = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category_id,
            domain_id=domain_id,
            persona_id=persona_id,
            summary="Legacy complaint row without founder signals.",
            verbatim_quote="Legacy complaint row without founder signals.",
            severity=3,
            llm_model="mock-classifier",
        )
    )

    assert created.business_function_code is None
    assert created.jtbd_code is None
    assert created.consequence_code is None
