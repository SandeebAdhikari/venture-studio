"""Integration tests for growth strategy service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.growth_strategy.mock_client import (
    MockGrowthStrategyLLMClient,
    default_mock_growth_strategy_output,
)
from app.agents.growth_strategy.service import GrowthStrategyService
from app.config import Settings
from app.db.enums import CategoryKind, GrowthEvaluationStatus, SourceType
from app.db.models.category import Category
from app.db.models.growth_evaluation import GrowthEvaluation
from app.db.models.growth_evaluation_evidence import GrowthEvaluationEvidence
from app.db.models.llm_call import LLMCall
from app.db.models.opportunity import Opportunity
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


@pytest.fixture
def growth_strategy_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-growth-strategy",
        growth_strategy_model="mock-growth-strategy",
        growth_strategy_max_retries=2,
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
        name=f"growth-strategy-source-{uuid4()}",
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


@pytest.mark.asyncio
async def test_evaluate_opportunity_persists_scores_and_roadmap(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    growth_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockGrowthStrategyLLMClient([default_mock_growth_strategy_output()])
    service = GrowthStrategyService(repos, growth_strategy_settings, llm_client=mock)

    result = await service.evaluate_opportunity(opportunity.id)

    assert result.status == "completed"
    assert result.growth_evaluation_id is not None
    assert result.draft is not None
    assert result.draft.growth_score == 78
    assert result.draft.scalability_score == 71
    assert result.draft.risk_score == 42
    assert len(result.draft.growth_roadmap) == 3
    assert result.draft.evaluation_metrics["growth_readiness_score"] > 0

    evaluation = await repos.growth_evaluations.get_by_id_with_evidence(result.growth_evaluation_id)
    assert evaluation is not None
    assert evaluation.status == GrowthEvaluationStatus.COMPLETED.value
    assert evaluation.is_current is True
    assert len(evaluation.growth_roadmap) == 3
    assert len(evaluation.evidence) == 3
    assert evaluation.evidence[0].complaint_id is not None


@pytest.mark.asyncio
async def test_evaluate_opportunity_skips_when_already_evaluated(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    growth_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockGrowthStrategyLLMClient([default_mock_growth_strategy_output()])
    service = GrowthStrategyService(repos, growth_strategy_settings, llm_client=mock)

    first = await service.evaluate_opportunity(opportunity.id)
    second = await service.evaluate_opportunity(opportunity.id)

    assert first.status == "completed"
    assert second.status == "skipped"
    assert second.skip_reason == "already_evaluated"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_evaluate_pending_processes_unevaluated_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    growth_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockGrowthStrategyLLMClient([default_mock_growth_strategy_output()])
    service = GrowthStrategyService(repos, growth_strategy_settings, llm_client=mock)

    batch = await service.evaluate_pending(limit=10)

    assert batch.completed >= 1
    assert batch.items[0].opportunity_id == opportunity.id


@pytest.mark.asyncio
async def test_evaluate_logs_llm_calls(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    growth_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockGrowthStrategyLLMClient([default_mock_growth_strategy_output()])
    service = GrowthStrategyService(repos, growth_strategy_settings, llm_client=mock)

    await service.evaluate_opportunity(opportunity.id)

    count = await db_session.scalar(
        select(func.count())
        .select_from(LLMCall)
        .where(
            LLMCall.entity_id == opportunity.id,
            LLMCall.graph_name == "evaluate_growth_strategy",
        )
    )
    assert count == 1


@pytest.mark.asyncio
async def test_evaluate_retries_malformed_response(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    growth_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockGrowthStrategyLLMClient([None, default_mock_growth_strategy_output()])
    service = GrowthStrategyService(repos, growth_strategy_settings, llm_client=mock)

    result = await service.evaluate_opportunity(opportunity.id)

    assert result.status == "completed"
    assert mock.call_count == 2

    total_evaluations = await db_session.scalar(select(func.count()).select_from(GrowthEvaluation))
    total_evidence = await db_session.scalar(
        select(func.count()).select_from(GrowthEvaluationEvidence)
    )
    assert total_evaluations == 1
    assert total_evidence == 3
