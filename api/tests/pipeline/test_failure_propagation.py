"""Integration tests for pipeline failure propagation and stop_on_failure."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.market_research.schemas import MarketResearchBatchResult, MarketResearchResult
from app.config import Settings
from app.db.enums import (
    CategoryKind,
    PipelineRunStatus,
    PipelineStage,
    PipelineStageStatus,
    SourceType,
)
from app.db.models.category import Category
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.pipeline.executor import PipelineStageExecutor
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.schemas import StageOutcome
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate
from app.schemas.pipeline import PipelineRunOptions
from app.services.container import ServiceContainer


@pytest.fixture
def pipeline_settings() -> Settings:
    return Settings(
        api_key="test-failure-propagation-key",
        pipeline_max_retries=0,
        pipeline_retry_backoff_sec=0.01,
        require_founder_approval=False,
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


@pytest.fixture
async def research_opportunity_id(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> UUID:
    category_id, domain_id, persona_id = taxonomy_ids
    repos = get_repositories(db_session)

    source = Source(
        name=f"failure-prop-source-{uuid4()}",
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
        title="Export pain",
        body="Export workflow is broken for our team.",
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
            summary="Export workflow is broken for our team.",
            verbatim_quote="Export workflow is broken for our team.",
            severity=4,
            product_mentions=[],
            llm_model="test-classifier",
            llm_confidence=0.9,
        )
    )

    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title=f"Failure Prop SaaS {uuid4()}",
            problem_statement="Teams cannot export operational data.",
            target_user="Ops admins",
            frequency_signal="Repeated export complaints.",
            existing_alternatives="Manual CSV hacks.",
            gap="Reliable export automation.",
            confidence_score=0.8,
            llm_model="test-generator",
            complaint_ids=[complaint.id],
        )
    )
    return opportunity.id


def _build_orchestrator(
    db_session: AsyncSession,
    settings: Settings,
    *,
    opportunity_id: UUID,
) -> tuple[PipelineOrchestrator, ServiceContainer]:
    repos = get_repositories(db_session)
    services = ServiceContainer(repos)

    async def failing_research_pending(
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> MarketResearchBatchResult:
        batch = MarketResearchBatchResult(opportunities_found=1)
        batch.add(
            MarketResearchResult(
                opportunity_id=opportunity_id,
                status="failed",
                error="simulated LLM failure",
            )
        )
        return batch

    services.market_research.research_pending = failing_research_pending  # type: ignore[method-assign]
    orchestrator = PipelineOrchestrator(repos, services, settings)
    return orchestrator, services


@pytest.mark.asyncio
async def test_executor_marks_agent_batch_as_failed(
    db_session: AsyncSession,
    pipeline_settings: Settings,
    research_opportunity_id: UUID,
) -> None:
    repos = get_repositories(db_session)
    services = ServiceContainer(repos)

    async def failing_research_pending(
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> MarketResearchBatchResult:
        batch = MarketResearchBatchResult(opportunities_found=1)
        batch.add(
            MarketResearchResult(
                opportunity_id=research_opportunity_id,
                status="failed",
                error="simulated LLM failure",
            )
        )
        return batch

    services.market_research.research_pending = failing_research_pending  # type: ignore[method-assign]
    executor = PipelineStageExecutor(repos, services, pipeline_settings)

    result = await executor.execute(
        PipelineStage.MARKET_RESEARCH,
        PipelineRunOptions(force=True),
    )

    assert result.items_in == 1
    assert result.items_out == 0
    assert result.items_failed == 1
    assert result.failed is True
    assert result.metadata["outcome"] == StageOutcome.FAILED.value
    assert result.error is not None


@pytest.mark.asyncio
async def test_stop_on_failure_stops_after_failed_agent_stage(
    db_session: AsyncSession,
    pipeline_settings: Settings,
    research_opportunity_id: UUID,
) -> None:
    orchestrator, _ = _build_orchestrator(
        db_session,
        pipeline_settings,
        opportunity_id=research_opportunity_id,
    )
    downstream = [
        PipelineStage.MARKET_RESEARCH,
        PipelineStage.COMPETITOR_ANALYSIS,
    ]

    result = await orchestrator.run_pipeline(
        options=PipelineRunOptions(
            stages_only=downstream,
            stop_on_failure=True,
            force=True,
        ),
    )

    assert result.status == PipelineRunStatus.FAILED
    assert result.stages_failed == 1
    assert result.stages_skipped == 1

    detail = await orchestrator.get_run(result.pipeline_run_id)
    market_stage = next(
        stage for stage in detail.stage_runs if stage.stage == PipelineStage.MARKET_RESEARCH
    )
    assert market_stage.status == PipelineStageStatus.FAILED
    assert market_stage.items_out == 0
    assert market_stage.items_failed == 1
    assert market_stage.stage_metadata.get("outcome") == StageOutcome.FAILED.value

    competitor_stage = next(
        stage
        for stage in detail.stage_runs
        if stage.stage == PipelineStage.COMPETITOR_ANALYSIS
    )
    assert competitor_stage.status == PipelineStageStatus.SKIPPED
    assert competitor_stage.stage_metadata.get("skip_reason") == "prior_stage_failure"


@pytest.mark.asyncio
async def test_stop_on_failure_false_runs_downstream_after_agent_failure(
    db_session: AsyncSession,
    pipeline_settings: Settings,
    research_opportunity_id: UUID,
) -> None:
    from app.pipeline.schemas import StageExecutionResult

    orchestrator, _ = _build_orchestrator(
        db_session,
        pipeline_settings,
        opportunity_id=research_opportunity_id,
    )

    executed_stages: list[PipelineStage] = []
    original_execute = orchestrator._executor.execute

    async def tracking_execute(stage: PipelineStage, opts=None):
        executed_stages.append(stage)
        if stage == PipelineStage.MARKET_RESEARCH:
            return await original_execute(stage, opts)
        return StageExecutionResult(items_out=0, metadata={"outcome": "completed"})

    orchestrator._executor.execute = tracking_execute  # type: ignore[method-assign]

    downstream = [
        PipelineStage.MARKET_RESEARCH,
        PipelineStage.COMPETITOR_ANALYSIS,
        PipelineStage.CUSTOMER_RESEARCH,
    ]
    result = await orchestrator.run_pipeline(
        options=PipelineRunOptions(
            stages_only=downstream,
            stop_on_failure=False,
            force=True,
        ),
    )

    assert result.stages_failed == 1
    assert executed_stages[0] == PipelineStage.MARKET_RESEARCH
    assert executed_stages[1:] == [
        PipelineStage.COMPETITOR_ANALYSIS,
        PipelineStage.CUSTOMER_RESEARCH,
    ]

    detail = await orchestrator.get_run(result.pipeline_run_id)
    competitor_stage = next(
        stage
        for stage in detail.stage_runs
        if stage.stage == PipelineStage.COMPETITOR_ANALYSIS
    )
    assert competitor_stage.status == PipelineStageStatus.COMPLETED


@pytest.mark.asyncio
async def test_agent_batch_all_skipped_is_completed_not_failed(
    db_session: AsyncSession,
    pipeline_settings: Settings,
    research_opportunity_id: UUID,
) -> None:
    repos = get_repositories(db_session)
    services = ServiceContainer(repos)

    async def skipped_research_pending(
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> MarketResearchBatchResult:
        batch = MarketResearchBatchResult(opportunities_found=1)
        batch.add(
            MarketResearchResult(
                opportunity_id=research_opportunity_id,
                status="skipped",
                skip_reason="already_researched",
            )
        )
        return batch

    services.market_research.research_pending = skipped_research_pending  # type: ignore[method-assign]
    executor = PipelineStageExecutor(repos, services, pipeline_settings)

    result = await executor.execute(
        PipelineStage.MARKET_RESEARCH,
        PipelineRunOptions(force=False),
    )

    assert result.items_in == 1
    assert result.items_out == 0
    assert result.items_failed == 0
    assert result.metadata["skipped"] == 1
    assert result.failed is False
    assert result.metadata["outcome"] == StageOutcome.SKIPPED.value
