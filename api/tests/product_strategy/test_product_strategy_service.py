"""Integration tests for product strategy service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.product_strategy.mock_client import (
    MockProductStrategyLLMClient,
    default_mock_product_strategy_output,
)
from app.agents.product_strategy.service import ProductStrategyService
from app.config import Settings
from app.db.enums import CategoryKind, ProductStrategyStatus, SourceType
from app.db.models.category import Category
from app.db.models.llm_call import LLMCall
from app.db.models.opportunity import Opportunity
from app.db.models.product_strategy import ProductStrategy
from app.db.models.product_strategy_evidence import ProductStrategyEvidence
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


@pytest.fixture
def product_strategy_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-product-strategy",
        product_strategy_model="mock-product-strategy",
        product_strategy_max_retries=2,
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
        name=f"product-strategy-source-{uuid4()}",
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
async def test_plan_opportunity_persists_strategy_and_roadmap(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    product_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockProductStrategyLLMClient([default_mock_product_strategy_output()])
    service = ProductStrategyService(repos, product_strategy_settings, llm_client=mock)

    result = await service.plan_opportunity(opportunity.id)

    assert result.status == "completed"
    assert result.product_strategy_id is not None
    assert result.draft is not None
    assert len(result.draft.core_features) == 3
    assert len(result.draft.roadmap) == 3
    assert result.draft.planning_metrics["planning_readiness_score"] > 0

    strategy = await repos.product_strategies.get_by_id_with_evidence(result.product_strategy_id)
    assert strategy is not None
    assert strategy.status == ProductStrategyStatus.COMPLETED.value
    assert strategy.is_current is True
    assert len(strategy.roadmap) == 3
    assert len(strategy.evidence) == 3
    assert strategy.evidence[0].complaint_id is not None


@pytest.mark.asyncio
async def test_plan_opportunity_skips_when_already_planned(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    product_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockProductStrategyLLMClient([default_mock_product_strategy_output()])
    service = ProductStrategyService(repos, product_strategy_settings, llm_client=mock)

    first = await service.plan_opportunity(opportunity.id)
    second = await service.plan_opportunity(opportunity.id)

    assert first.status == "completed"
    assert second.status == "skipped"
    assert second.skip_reason == "already_planned"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_plan_pending_processes_unplanned_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    product_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockProductStrategyLLMClient([default_mock_product_strategy_output()])
    service = ProductStrategyService(repos, product_strategy_settings, llm_client=mock)

    batch = await service.plan_pending(limit=10)

    assert batch.completed >= 1
    assert batch.items[0].opportunity_id == opportunity.id


@pytest.mark.asyncio
async def test_plan_logs_llm_calls(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    product_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockProductStrategyLLMClient([default_mock_product_strategy_output()])
    service = ProductStrategyService(repos, product_strategy_settings, llm_client=mock)

    await service.plan_opportunity(opportunity.id)

    count = await db_session.scalar(
        select(func.count())
        .select_from(LLMCall)
        .where(
            LLMCall.entity_id == opportunity.id,
            LLMCall.graph_name == "plan_product_strategy",
        )
    )
    assert count == 1


@pytest.mark.asyncio
async def test_plan_retries_malformed_response(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    product_strategy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockProductStrategyLLMClient([None, default_mock_product_strategy_output()])
    service = ProductStrategyService(repos, product_strategy_settings, llm_client=mock)

    result = await service.plan_opportunity(opportunity.id)

    assert result.status == "completed"
    assert mock.call_count == 2

    total_strategies = await db_session.scalar(select(func.count()).select_from(ProductStrategy))
    total_evidence = await db_session.scalar(
        select(func.count()).select_from(ProductStrategyEvidence)
    )
    assert total_strategies == 1
    assert total_evidence == 3
