"""Integration tests for opportunity generator service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.opportunity.mock_client import MockOpportunityLLMClient
from app.agents.opportunity.schemas import OpportunityLLMOutput
from app.agents.opportunity.service import OpportunityGeneratorService
from app.config import Settings
from app.db.enums import PipelineStage
from app.logging import configure_logging
from app.pipeline.executor import PipelineStageExecutor
from app.services.container import ServiceContainer
from app.db.enums import CategoryKind, SourceType
from app.db.models.category import Category
from app.db.models.complaint import Complaint
from app.db.models.llm_call import LLMCall
from app.db.models.opportunity import Opportunity
from app.db.models.opportunity_score import OpportunityScore
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate


@pytest.fixture
def generation_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-generation",
        min_cluster_size=3,
        generation_model="mock-generator",
        min_opportunity_confidence=0.4,
        min_avg_severity=2.0,
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


async def _create_complaint(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    *,
    summary: str,
    severity: int = 4,
) -> Complaint:
    category_id, domain_id, persona_id = taxonomy_ids
    source = Source(
        name=f"generation-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "smallbusiness"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url=f"https://example.com/posts/{uuid4()}",
        title="Scheduling pain",
        body=summary,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    return await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category_id,
            domain_id=domain_id,
            persona_id=persona_id,
            summary=summary,
            verbatim_quote=summary[:80],
            severity=severity,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )


def _staff_scheduling_output(count: int) -> OpportunityLLMOutput:
    return OpportunityLLMOutput(
        title="Staff Scheduling SaaS",
        problem_statement=(
            "Operations teams repeatedly struggle with staff scheduling across shifts "
            "and last-minute changes."
        ),
        target_user="Ops admins at multi-location service businesses",
        frequency_signal=f"{count} complaints mention staff scheduling coordination pain.",
        existing_alternatives="Teams mention ShiftApp and spreadsheets in the evidence.",
        gap="No lightweight scheduling workflow tailored to hourly staff coordination.",
        confidence_score=0.86,
        explanation=(
            "Recurring staff scheduling complaints show a clear, repeated pain that "
            "could support a focused SaaS product."
        ),
    )


@pytest.mark.asyncio
async def test_generate_creates_opportunity_with_linked_complaints(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    generation_settings: Settings,
) -> None:
    summaries = [
        "Staff scheduling breaks every week when employees swap shifts without notice.",
        "Our staff scheduling process fails whenever someone calls out sick on short notice.",
        "Staff scheduling takes hours because managers rebuild shifts in spreadsheets.",
        "Staff scheduling conflicts cause overtime and missed coverage across stores.",
    ]
    complaints = [
        await _create_complaint(db_session, taxonomy_ids, summary=summary) for summary in summaries
    ]

    repos = get_repositories(db_session)
    mock = MockOpportunityLLMClient([_staff_scheduling_output(len(summaries))])
    service = OpportunityGeneratorService(repos, generation_settings, llm_client=mock)

    result = await service.generate(limit=50)

    assert result.patterns_found >= 1
    assert result.created == 1
    created = result.items[0]
    assert created.status == "created"
    assert created.opportunity_id is not None
    assert created.draft is not None
    assert created.draft.title == "Staff Scheduling SaaS"

    opportunity = await repos.opportunities.get_by_id_with_relations(created.opportunity_id)
    assert opportunity is not None
    assert len(opportunity.complaints) == len(complaints)
    assert opportunity.confidence_score == pytest.approx(0.86)

    score = await repos.opportunity_scores.get_current_for_opportunity(opportunity.id)
    assert score is not None
    assert score.scoring_notes == created.draft.explanation
    assert score.frequency_score > 0


@pytest.mark.asyncio
async def test_generate_skips_low_confidence(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    generation_settings: Settings,
) -> None:
    for _ in range(3):
        await _create_complaint(
            db_session,
            taxonomy_ids,
            summary="Staff scheduling is chaotic when managers rebuild shifts manually.",
        )

    repos = get_repositories(db_session)
    mock = MockOpportunityLLMClient(
        [_staff_scheduling_output(3).model_copy(update={"confidence_score": 0.2})]
    )
    service = OpportunityGeneratorService(repos, generation_settings, llm_client=mock)

    result = await service.generate(limit=50)

    assert result.created == 0
    assert result.skipped >= 1
    assert result.items[0].skip_reason == "low_confidence"


@pytest.mark.asyncio
async def test_generate_logs_llm_calls(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    generation_settings: Settings,
) -> None:
    for _ in range(3):
        await _create_complaint(
            db_session,
            taxonomy_ids,
            summary="Staff scheduling fails when part-time staff availability changes daily.",
        )

    repos = get_repositories(db_session)
    mock = MockOpportunityLLMClient([_staff_scheduling_output(3)])
    service = OpportunityGeneratorService(repos, generation_settings, llm_client=mock)
    batch = await service.generate(limit=50)
    opportunity_id = batch.items[0].opportunity_id
    assert opportunity_id is not None

    count = await db_session.scalar(
        select(func.count())
        .select_from(LLMCall)
        .where(LLMCall.entity_id == opportunity_id, LLMCall.graph_name == "generate_opportunity")
    )
    assert count == 1


@pytest.mark.asyncio
async def test_generate_retries_malformed_response(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    generation_settings: Settings,
) -> None:
    for _ in range(3):
        await _create_complaint(
            db_session,
            taxonomy_ids,
            summary="Staff scheduling conflicts create coverage gaps every weekend.",
        )

    repos = get_repositories(db_session)
    mock = MockOpportunityLLMClient([None, _staff_scheduling_output(3)])
    service = OpportunityGeneratorService(repos, generation_settings, llm_client=mock)

    result = await service.generate(limit=50)

    assert result.created == 1
    assert mock.call_count == 2

    total_opportunities = await db_session.scalar(select(func.count()).select_from(Opportunity))
    assert total_opportunities == 1

    total_scores = await db_session.scalar(select(func.count()).select_from(OpportunityScore))
    assert total_scores == 1


@pytest.mark.asyncio
async def test_generate_completes_with_configured_json_logging(
    db_session: AsyncSession,
    generation_settings: Settings,
) -> None:
    """Regression: batch-complete log must not use reserved LogRecord key 'created'."""
    configure_logging(generation_settings.model_copy(update={"log_json": True, "log_level": "INFO"}))

    repos = get_repositories(db_session)
    service = OpportunityGeneratorService(repos, generation_settings, llm_client=MockOpportunityLLMClient([]))

    result = await service.generate(limit=50)

    assert result.created == 0
    assert result.failed == 0


@pytest.mark.asyncio
async def test_pipeline_generate_opportunities_stage_completes_with_json_logging(
    db_session: AsyncSession,
    generation_settings: Settings,
) -> None:
    """Regression: GENERATE_OPPORTUNITIES must complete when app logging is configured."""
    configure_logging(generation_settings.model_copy(update={"log_json": True, "log_level": "INFO"}))

    repos = get_repositories(db_session)
    services = ServiceContainer(repos)
    services.generation = OpportunityGeneratorService(
        repos, generation_settings, llm_client=MockOpportunityLLMClient([]),
    )
    executor = PipelineStageExecutor(repos, services, generation_settings)

    stage_result = await executor.execute(PipelineStage.GENERATE_OPPORTUNITIES)

    assert stage_result.failed is False
    assert stage_result.items_out == 0
    assert stage_result.items_failed == 0
