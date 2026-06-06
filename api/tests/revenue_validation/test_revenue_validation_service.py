"""Integration tests for revenue validation service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.competitor_intelligence.mock_client import (
    MockCompetitorIntelligenceLLMClient,
    default_mock_competitor_output,
)
from app.agents.competitor_intelligence.service import CompetitorIntelligenceService
from app.agents.revenue_validation.mock_client import (
    MockRevenueValidationLLMClient,
    default_mock_revenue_validation_output,
)
from app.agents.revenue_validation.service import RevenueValidationService
from app.config import Settings
from app.db.enums import CategoryKind, RevenueValidationStatus, SourceType
from app.db.models.category import Category
from app.db.models.llm_call import LLMCall
from app.db.models.opportunity import Opportunity
from app.db.models.revenue_validation import RevenueValidation
from app.db.models.revenue_validation_evidence import RevenueValidationEvidence
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


@pytest.fixture
def revenue_validation_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-revenue-validation",
        revenue_validation_model="mock-revenue-validation",
        revenue_validation_max_retries=2,
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
        name=f"revenue-validation-source-{uuid4()}",
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
        body=QUOTE,
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
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=QUOTE,
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


async def _seed_competitor_analysis(
    db_session: AsyncSession,
    opportunity: Opportunity,
    settings: Settings,
) -> None:
    repos = get_repositories(db_session)
    competitor_service = CompetitorIntelligenceService(
        repos,
        settings,
        llm_client=MockCompetitorIntelligenceLLMClient([default_mock_competitor_output()]),
    )
    result = await competitor_service.analyze_opportunity(opportunity.id)
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_validate_opportunity_persists_scores_and_evidence(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockRevenueValidationLLMClient(
        [default_mock_revenue_validation_output(include_competitor_pricing=False)]
    )
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    result = await service.validate_opportunity(opportunity.id)

    assert result.status == "completed"
    assert result.revenue_validation_id is not None
    assert result.draft is not None
    assert result.draft.willingness_to_pay_score == 74
    assert result.draft.revenue_confidence_score == 68
    assert result.draft.evaluation_metrics["evaluation_readiness_score"] > 0
    assert len(result.draft.pricing_recommendations) == 2

    validation = await repos.revenue_validations.get_by_id_with_evidence(
        result.revenue_validation_id
    )
    assert validation is not None
    assert validation.status == RevenueValidationStatus.COMPLETED.value
    assert validation.is_current is True
    assert len(validation.evidence) == 3
    assert validation.evidence[0].complaint_id is not None


@pytest.mark.asyncio
async def test_validate_opportunity_with_competitor_pricing_context(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    await _seed_competitor_analysis(db_session, opportunity, revenue_validation_settings)
    repos = get_repositories(db_session)
    mock = MockRevenueValidationLLMClient(
        [default_mock_revenue_validation_output(include_competitor_pricing=True)]
    )
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    result = await service.validate_opportunity(opportunity.id)

    assert result.status == "completed"
    validation = await repos.revenue_validations.get_by_id_with_evidence(
        result.revenue_validation_id
    )
    assert validation is not None
    assert len(validation.evidence) == 4
    assert any(item.competitor_profile_id is not None for item in validation.evidence)


@pytest.mark.asyncio
async def test_validate_opportunity_skips_when_already_validated(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockRevenueValidationLLMClient(
        [default_mock_revenue_validation_output(include_competitor_pricing=False)]
    )
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    first = await service.validate_opportunity(opportunity.id)
    second = await service.validate_opportunity(opportunity.id)

    assert first.status == "completed"
    assert second.status == "skipped"
    assert second.skip_reason == "already_validated"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_validate_pending_processes_unvalidated_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockRevenueValidationLLMClient(
        [default_mock_revenue_validation_output(include_competitor_pricing=False)]
    )
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    batch = await service.validate_pending(limit=10)

    assert batch.completed >= 1
    assert batch.items[0].opportunity_id == opportunity.id


@pytest.mark.asyncio
async def test_validate_logs_llm_calls(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockRevenueValidationLLMClient(
        [default_mock_revenue_validation_output(include_competitor_pricing=False)]
    )
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    await service.validate_opportunity(opportunity.id)

    count = await db_session.scalar(
        select(func.count())
        .select_from(LLMCall)
        .where(
            LLMCall.entity_id == opportunity.id,
            LLMCall.graph_name == "validate_revenue",
        )
    )
    assert count == 1


@pytest.mark.asyncio
async def test_validate_retries_malformed_response(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockRevenueValidationLLMClient(
        [None, default_mock_revenue_validation_output(include_competitor_pricing=False)]
    )
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    result = await service.validate_opportunity(opportunity.id)

    assert result.status == "completed"
    assert mock.call_count == 2

    total_validations = await db_session.scalar(select(func.count()).select_from(RevenueValidation))
    total_evidence = await db_session.scalar(
        select(func.count()).select_from(RevenueValidationEvidence)
    )
    assert total_validations == 1
    assert total_evidence == 3


@pytest.mark.asyncio
async def test_validate_opportunity_succeeds_with_uuid_derived_complaint_index(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    bad_output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    bad_output.supporting_evidence[0].complaint_index = 926
    bad_output.supporting_evidence[1].complaint_index = 37
    mock = MockRevenueValidationLLMClient([bad_output])
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    result = await service.validate_opportunity(opportunity.id)

    assert result.status == "completed"
    assert result.revenue_validation_id is not None
    assert result.draft is not None
    assert result.draft.supporting_evidence[0].complaint_index == 0


@pytest.mark.asyncio
async def test_validate_persists_llm_logs_on_validation_failure(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    revenue_validation_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    bad_output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    bad_output.executive_summary = "too short"
    mock = MockRevenueValidationLLMClient([bad_output, bad_output])
    service = RevenueValidationService(repos, revenue_validation_settings, llm_client=mock)

    result = await service.validate_opportunity(opportunity.id)

    assert result.status == "failed"
    count = await db_session.scalar(
        select(func.count())
        .select_from(LLMCall)
        .where(
            LLMCall.entity_id == opportunity.id,
            LLMCall.graph_name == "validate_revenue",
        )
    )
    assert count == 2
    calls = (
        await db_session.scalars(
            select(LLMCall).where(
                LLMCall.entity_id == opportunity.id,
                LLMCall.graph_name == "validate_revenue",
            )
        )
    ).all()
    assert any(
        call.error_detail
        or (call.eval_metadata or {}).get("validation_errors")
        or (call.eval_metadata or {}).get("failure_error")
        for call in calls
    )
