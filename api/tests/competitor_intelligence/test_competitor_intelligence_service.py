"""Integration tests for competitor intelligence service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.competitor_intelligence.mock_client import (
    MockCompetitorIntelligenceLLMClient,
    default_mock_competitor_output,
)
from app.agents.competitor_intelligence.service import CompetitorIntelligenceService
from app.config import Settings
from app.db.enums import CategoryKind, CompetitorAnalysisStatus, SourceType
from app.db.models.category import Category
from app.db.models.competitor_analysis import CompetitorAnalysis
from app.db.models.competitor_profile import CompetitorProfile
from app.db.models.llm_call import LLMCall
from app.db.models.opportunity import Opportunity
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate


@pytest.fixture
def competitor_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-competitor",
        competitor_model="mock-competitor",
        competitor_max_retries=2,
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
        name=f"competitor-source-{uuid4()}",
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
            summary="Staff scheduling breaks every week when using ShiftApp.",
            verbatim_quote="Staff scheduling breaks every week when using ShiftApp.",
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
async def test_analyze_opportunity_persists_profiles_and_gaps(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    competitor_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockCompetitorIntelligenceLLMClient([default_mock_competitor_output()])
    service = CompetitorIntelligenceService(repos, competitor_settings, llm_client=mock)

    result = await service.analyze_opportunity(opportunity.id)

    assert result.status == "completed"
    assert result.competitor_analysis_id is not None
    assert result.draft is not None
    assert len(result.draft.competitors) == 2
    assert result.draft.evaluation_metrics["competitor_count"] == 2

    analysis = await repos.competitor_analyses.get_by_id_with_profiles(
        result.competitor_analysis_id
    )
    assert analysis is not None
    assert analysis.status == CompetitorAnalysisStatus.COMPLETED.value
    assert analysis.is_current is True
    assert len(analysis.profiles) == 2
    assert len(analysis.competitive_gaps) == 1
    assert analysis.profiles[0].pricing_model["model_type"] == "subscription"
    assert analysis.evaluation_metrics["threat_level"] in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_analyze_opportunity_skips_when_already_analyzed(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    competitor_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockCompetitorIntelligenceLLMClient([default_mock_competitor_output()])
    service = CompetitorIntelligenceService(repos, competitor_settings, llm_client=mock)

    first = await service.analyze_opportunity(opportunity.id)
    second = await service.analyze_opportunity(opportunity.id)

    assert first.status == "completed"
    assert second.status == "skipped"
    assert second.skip_reason == "already_analyzed"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_analyze_opportunity_force_creates_new_version(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    competitor_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockCompetitorIntelligenceLLMClient(
        [default_mock_competitor_output(), default_mock_competitor_output()]
    )
    service = CompetitorIntelligenceService(repos, competitor_settings, llm_client=mock)

    await service.analyze_opportunity(opportunity.id)
    result = await service.analyze_opportunity(opportunity.id, force=True)

    assert result.status == "completed"
    history = await repos.competitor_analyses.list_for_opportunity(opportunity.id)
    assert len(history) == 2
    assert history[0].version == 2
    assert history[0].is_current is True
    assert history[1].is_current is False


@pytest.mark.asyncio
async def test_analyze_pending_processes_unanalyzed_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    competitor_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockCompetitorIntelligenceLLMClient([default_mock_competitor_output()])
    service = CompetitorIntelligenceService(repos, competitor_settings, llm_client=mock)

    batch = await service.analyze_pending(limit=10)

    assert batch.opportunities_found >= 1
    assert batch.completed >= 1
    assert batch.items[0].opportunity_id == opportunity.id


@pytest.mark.asyncio
async def test_analyze_logs_llm_calls_with_evaluation_metrics(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    competitor_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockCompetitorIntelligenceLLMClient([default_mock_competitor_output()])
    service = CompetitorIntelligenceService(repos, competitor_settings, llm_client=mock)

    await service.analyze_opportunity(opportunity.id)

    llm_call = await db_session.scalar(
        select(LLMCall).where(
            LLMCall.entity_id == opportunity.id,
            LLMCall.graph_name == "analyze_competitors",
        )
    )
    assert llm_call is not None
    assert llm_call.eval_metadata.get("evaluation_metrics") is not None


@pytest.mark.asyncio
async def test_analyze_retries_malformed_response(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    competitor_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockCompetitorIntelligenceLLMClient([None, default_mock_competitor_output()])
    service = CompetitorIntelligenceService(repos, competitor_settings, llm_client=mock)

    result = await service.analyze_opportunity(opportunity.id)

    assert result.status == "completed"
    assert mock.call_count == 2

    total_analyses = await db_session.scalar(select(func.count()).select_from(CompetitorAnalysis))
    total_profiles = await db_session.scalar(select(func.count()).select_from(CompetitorProfile))
    assert total_analyses == 1
    assert total_profiles == 2
