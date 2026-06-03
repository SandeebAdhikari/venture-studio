"""Integration tests for market research service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.market_research.mock_client import (
    MockMarketResearchLLMClient,
    default_mock_research_output,
)
from app.agents.market_research.service import MarketResearchService
from app.config import Settings
from app.db.enums import CategoryKind, MarketResearchStatus, SourceType
from app.db.models.category import Category
from app.db.models.complaint import Complaint
from app.db.models.llm_call import LLMCall
from app.db.models.market_brief import MarketBrief
from app.db.models.opportunity import Opportunity
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate


@pytest.fixture
def research_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-research",
        research_model="mock-research",
        research_max_retries=2,
    )


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
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None
    return category.id, domain.id, persona.id


async def _create_opportunity(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> Opportunity:
    category_id, domain_id, persona_id = taxonomy_ids
    source = Source(
        name=f"research-source-{uuid4()}",
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
        title="Scheduling pain",
        body="Staff scheduling is broken",
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category_id,
            domain_id=domain_id,
            persona_id=persona_id,
            summary="Staff scheduling breaks every week across locations.",
            verbatim_quote="Staff scheduling breaks every week across locations.",
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )

    return await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Ops teams struggle with hourly staff scheduling.",
            target_user="Ops admins at multi-location service businesses",
            frequency_signal="Multiple complaints mention scheduling coordination pain.",
            existing_alternatives="Teams mention ShiftApp and spreadsheets.",
            gap="No lightweight scheduling workflow for hourly staff.",
            confidence_score=0.86,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )


@pytest.mark.asyncio
async def test_research_opportunity_persists_market_brief(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    research_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockMarketResearchLLMClient([default_mock_research_output()])
    service = MarketResearchService(repos, research_settings, llm_client=mock)

    result = await service.research_opportunity(opportunity.id)

    assert result.status == "completed"
    assert result.market_brief_id is not None
    assert result.draft is not None
    assert result.draft.tam_usd == pytest.approx(4_500_000_000)
    assert len(result.draft.customer_segments) == 2
    assert len(result.draft.supporting_evidence) >= 1

    brief = await repos.market_briefs.get_by_id(result.market_brief_id)
    assert brief is not None
    assert brief.status == MarketResearchStatus.COMPLETED.value
    assert brief.is_current is True
    assert brief.version == 1
    assert brief.market_size_usd == pytest.approx(12_000_000_000)
    assert brief.research_metadata["graph_name"] == "research_market"


@pytest.mark.asyncio
async def test_research_opportunity_skips_when_already_researched(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    research_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockMarketResearchLLMClient([default_mock_research_output()])
    service = MarketResearchService(repos, research_settings, llm_client=mock)

    first = await service.research_opportunity(opportunity.id)
    second = await service.research_opportunity(opportunity.id)

    assert first.status == "completed"
    assert second.status == "skipped"
    assert second.skip_reason == "already_researched"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_research_opportunity_force_creates_new_version(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    research_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockMarketResearchLLMClient([default_mock_research_output(), default_mock_research_output()])
    service = MarketResearchService(repos, research_settings, llm_client=mock)

    await service.research_opportunity(opportunity.id)
    result = await service.research_opportunity(opportunity.id, force=True)

    assert result.status == "completed"
    history = await repos.market_briefs.list_for_opportunity(opportunity.id)
    assert len(history) == 2
    assert history[0].version == 2
    assert history[0].is_current is True
    assert history[1].is_current is False


@pytest.mark.asyncio
async def test_research_pending_processes_unresearched_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    research_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockMarketResearchLLMClient([default_mock_research_output()])
    service = MarketResearchService(repos, research_settings, llm_client=mock)

    batch = await service.research_pending(limit=10)

    assert batch.opportunities_found >= 1
    assert batch.completed >= 1
    assert batch.items[0].opportunity_id == opportunity.id


@pytest.mark.asyncio
async def test_research_logs_llm_calls(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    research_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockMarketResearchLLMClient([default_mock_research_output()])
    service = MarketResearchService(repos, research_settings, llm_client=mock)

    await service.research_opportunity(opportunity.id)

    count = await db_session.scalar(
        select(func.count())
        .select_from(LLMCall)
        .where(
            LLMCall.entity_id == opportunity.id,
            LLMCall.graph_name == "research_market",
        )
    )
    assert count == 1


@pytest.mark.asyncio
async def test_research_retries_malformed_response(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    research_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockMarketResearchLLMClient([None, default_mock_research_output()])
    service = MarketResearchService(repos, research_settings, llm_client=mock)

    result = await service.research_opportunity(opportunity.id)

    assert result.status == "completed"
    assert mock.call_count == 2

    total_briefs = await db_session.scalar(select(func.count()).select_from(MarketBrief))
    assert total_briefs == 1
