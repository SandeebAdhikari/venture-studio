"""Integration tests for opportunity scoring service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CategoryKind, SourceType
from app.db.models.category import Category
from app.db.models.opportunity import Opportunity
from app.db.models.opportunity_score import OpportunityScore
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate
from app.scoring.service import OpportunityScoringService


@pytest.fixture
async def taxonomy_ids(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "devtools",
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


async def _create_scored_opportunity(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    *,
    complaint_count: int = 5,
) -> Opportunity:
    category_id, domain_id, persona_id = taxonomy_ids
    repos = get_repositories(db_session)

    source = Source(
        name=f"scoring-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    complaint_ids: list[UUID] = []
    for index in range(complaint_count):
        signal = Signal(
            source_id=source.id,
            external_id=f"ext-{uuid4()}",
            url=f"https://example.com/posts/{uuid4()}",
            title="Staff scheduling pain",
            body=f"Staff scheduling issue #{index}",
            processing_status="classified",
        )
        db_session.add(signal)
        await db_session.flush()

        complaint = await repos.complaints.create(
            ComplaintCreate(
                signal_id=signal.id,
                category_id=category_id,
                domain_id=domain_id,
                persona_id=persona_id,
                summary="Staff scheduling breaks when managers rebuild shifts manually.",
                verbatim_quote="Staff scheduling breaks when managers rebuild shifts manually.",
                severity=4,
                product_mentions=["ShiftApp"],
                llm_model="mock-classifier",
                llm_confidence=0.9,
            )
        )
        complaint_ids.append(complaint.id)

    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Founders managing hourly teams",
            frequency_signal=f"{complaint_count} complaints mention staff scheduling.",
            existing_alternatives="ShiftApp and spreadsheets appear in evidence.",
            gap="No lightweight staff scheduling workflow tailored to small teams.",
            confidence_score=0.86,
            llm_model="mock-generator",
            complaint_ids=complaint_ids,
        )
    )
    return opportunity


@pytest.mark.asyncio
async def test_score_opportunity_persists_0_to_100_score(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    opportunity = await _create_scored_opportunity(db_session, taxonomy_ids, complaint_count=10)
    service = OpportunityScoringService(get_repositories(db_session))

    record = await service.score_opportunity(opportunity.id)

    assert 0 <= record.score <= 100
    assert record.is_current is True
    assert record.dimensions.volume > 0
    assert record.dimensions.severity > 0
    assert record.scoring_model == "scoring_engine_v1"


@pytest.mark.asyncio
async def test_rescore_appends_history_and_marks_previous_not_current(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    opportunity = await _create_scored_opportunity(db_session, taxonomy_ids, complaint_count=8)
    repos = get_repositories(db_session)
    service = OpportunityScoringService(repos)

    first = await service.score_opportunity(opportunity.id)
    second = await service.rescore_opportunity(opportunity.id)

    assert first.id != second.id
    assert second.is_current is True

    history = await service.get_score_history(opportunity.id)
    assert len(history) == 2

    current_count = await db_session.scalar(
        select(func.count())
        .select_from(OpportunityScore)
        .where(
            OpportunityScore.opportunity_id == opportunity.id,
            OpportunityScore.is_current.is_(True),
        )
    )
    assert current_count == 1

    refreshed_first = await repos.opportunity_scores.get_by_id(first.id)
    assert refreshed_first is not None
    assert refreshed_first.is_current is False


@pytest.mark.asyncio
async def test_get_current_score_returns_latest(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    opportunity = await _create_scored_opportunity(db_session, taxonomy_ids)
    service = OpportunityScoringService(get_repositories(db_session))

    await service.score_opportunity(opportunity.id)
    latest = await service.rescore_opportunity(opportunity.id)
    current = await service.get_current_score(opportunity.id)

    assert current is not None
    assert current.id == latest.id
