"""Pipeline executor integration for VENTURE_REPORT stage (defect D1)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import CategoryKind, PipelineStage, ReportType, SourceType
from app.db.models.category import Category
from app.db.models.report import Report
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.pipeline.executor import PipelineStageExecutor
from app.pipeline.orchestrator import PipelineOrchestrator
from app.ranking.service import ExecutiveRankingService
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate
from app.schemas.pipeline import PipelineRunOptions
from app.services.container import ServiceContainer
from tests.ranking.test_executive_ranking_service import (
    AgentScoreProfile,
    _seed_agent_outputs,
)


@pytest.fixture
def pipeline_settings() -> Settings:
    return Settings(
        api_key="test-venture-report-executor-key",
        pipeline_max_retries=2,
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


async def _seed_ranked_opportunity(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    category_id, domain_id, persona_id = taxonomy_ids
    repos = get_repositories(db_session)

    source = Source(
        name=f"venture-pipeline-source-{uuid4()}",
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
        body="Scheduling chaos every week.",
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
            summary="Scheduling chaos from last-minute shift changes.",
            verbatim_quote="Scheduling chaos from last-minute shift changes.",
            severity=5,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )

    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title=f"Venture Pipeline SaaS {uuid4()}",
            problem_statement="Ops teams struggle with hourly staff scheduling.",
            target_user="Ops admins",
            frequency_signal="Repeated scheduling complaints.",
            existing_alternatives="ShiftApp and spreadsheets.",
            gap="No lightweight scheduling workflow.",
            confidence_score=0.86,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, AgentScoreProfile())
    await ExecutiveRankingService(repos).generate_ranking(top_n=5)


@pytest.mark.asyncio
async def test_executor_venture_report_stage_maps_content_fields(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    pipeline_settings: Settings,
) -> None:
    await _seed_ranked_opportunity(db_session, taxonomy_ids)

    repos = get_repositories(db_session)
    services = ServiceContainer(repos)
    executor = PipelineStageExecutor(repos, services, pipeline_settings)

    result = await executor.execute(PipelineStage.VENTURE_REPORT)

    assert result.failed is False
    assert result.items_out == 1
    assert result.records_processed >= 1
    assert "report_id" in result.metadata
    assert result.metadata.get("generated_count", 0) >= 1
    assert "ranking_run_id" in result.metadata


@pytest.mark.asyncio
async def test_pipeline_venture_report_stage_completes_with_single_report(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    pipeline_settings: Settings,
) -> None:
    await _seed_ranked_opportunity(db_session, taxonomy_ids)

    before = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )

    repos = get_repositories(db_session)
    orchestrator = PipelineOrchestrator(repos, ServiceContainer(repos), pipeline_settings)
    run = await orchestrator.run_pipeline(
        options=PipelineRunOptions(
            stages_only=[PipelineStage.VENTURE_REPORT],
            stop_on_failure=True,
        ),
    )

    assert run.stages_completed == 1
    assert run.stages_failed == 0

    detail = await orchestrator.get_run(run.pipeline_run_id)
    stage = detail.stage_runs[0]
    assert stage.stage == PipelineStage.VENTURE_REPORT
    assert stage.status.value == "completed"
    assert stage.attempt == 1
    assert stage.stage_metadata is not None
    assert "report_id" in stage.stage_metadata

    after = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )
    assert after - before == 1
