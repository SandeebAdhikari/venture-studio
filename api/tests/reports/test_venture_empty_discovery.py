"""Tests for empty-discovery venture report generation and zero-opportunity completion."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import ExecutiveRankingStatus, PipelineRunStatus, PipelineStage, PipelineTrigger
from app.db.models.opportunity import Opportunity
from app.pipeline.lineage import merge_pipeline_run_lineage
from app.pipeline.orchestrator import PipelineOrchestrator
from app.ranking.constants import RANKING_ENGINE
from app.reports.venture.funnel import VentureDiscoveryFunnel
from app.reports.venture.generator import VentureReportGenerator
from app.reports.venture.service import VentureReportService
from app.repositories import get_repositories
from app.schemas.executive_ranking import ExecutiveRankingRunCreate
from app.schemas.pipeline import PipelineRunCreate, PipelineRunOptions, PipelineStageRunCreate
from app.services.container import ServiceContainer


@pytest.fixture
def pipeline_settings() -> Settings:
    return Settings(
        api_key="test-empty-discovery-key",
        pipeline_max_retries=0,
        pipeline_retry_backoff_sec=0.01,
        require_founder_approval=False,
    )


def test_render_empty_discovery_markdown_includes_funnel() -> None:
    generator = VentureReportGenerator()
    funnel = VentureDiscoveryFunnel(
        signals_collected=89,
        complaints_extracted=35,
        patterns_found=0,
        opportunities_generated=0,
        ranked_opportunity_count=0,
    )
    markdown = generator.render_empty_discovery_markdown(
        funnel,
        generated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    assert "## Discovery funnel" in markdown
    assert "**Signals collected:** 89" in markdown
    assert "**Complaints extracted:** 35" in markdown
    assert "**Patterns found:** 0" in markdown
    assert "**Opportunities generated:** 0" in markdown
    assert "## Why no founder-grade opportunities" in markdown
    assert "coherence gates" in markdown


@pytest.mark.asyncio
async def test_generate_venture_report_with_empty_ranking(
    db_session: AsyncSession,
    pipeline_settings: Settings,
) -> None:
    repos = get_repositories(db_session)
    await db_session.execute(delete(Opportunity))
    await db_session.flush()

    run = await repos.pipelines.create_run(
        PipelineRunCreate(
            trigger=PipelineTrigger.API,
            config_snapshot={"test": "empty_discovery"},
        )
    )
    stages = [
        PipelineStageRunCreate(stage=stage, sequence=index, max_attempts=1)
        for index, stage in enumerate(
            [
                PipelineStage.COLLECT,
                PipelineStage.CLASSIFY,
                PipelineStage.GENERATE_OPPORTUNITIES,
                PipelineStage.EXECUTIVE_RANKING,
                PipelineStage.VENTURE_REPORT,
            ],
            start=1,
        )
    ]
    await repos.pipelines.create_stage_runs(run.id, stages)
    for stage, items_in, items_out in [
        (PipelineStage.COLLECT, 89, 89),
        (PipelineStage.CLASSIFY, 89, 35),
        (PipelineStage.GENERATE_OPPORTUNITIES, 0, 0),
    ]:
        stage_run = await repos.pipelines.get_stage_run(run.id, stage.value)
        assert stage_run is not None
        await repos.pipelines.mark_stage_started(stage_run)
        await repos.pipelines.mark_stage_completed(
            stage_run,
            items_in=items_in,
            items_out=items_out,
            items_failed=0,
            records_processed=1,
        )

    ranking_run = await repos.executive_rankings.create(
        ExecutiveRankingRunCreate(
            status=ExecutiveRankingStatus.COMPLETED,
            top_n=5,
            opportunity_count=0,
            ranked_opportunity_count=0,
            ranking_engine=RANKING_ENGINE,
            ranking_metadata=merge_pipeline_run_lineage({}, pipeline_run_id=run.id),
            entries=[],
        )
    )

    service = VentureReportService(repos, pipeline_settings)
    result = await service.generate_venture_report(
        top_n=5,
        ranking_run_id=ranking_run.id,
        generate_ranking_if_missing=False,
        pipeline_run_id=run.id,
    )

    assert result.content.generated_count == 0
    assert result.content.outcome == "empty_discovery"
    assert result.content.discovery_funnel is not None
    assert result.content.discovery_funnel.signals_collected == 89
    assert result.content.discovery_funnel.complaints_extracted == 35
    assert result.content.discovery_funnel.patterns_found == 0
    assert "**Signals collected:** 89" in result.markdown


@pytest.mark.asyncio
async def test_pipeline_completes_with_zero_opportunities(
    db_session: AsyncSession,
    pipeline_settings: Settings,
) -> None:
    repos = get_repositories(db_session)
    await db_session.execute(delete(Opportunity))
    await db_session.flush()

    orchestrator = PipelineOrchestrator(repos, ServiceContainer(repos), pipeline_settings)

    result = await orchestrator.run_pipeline(
        options=PipelineRunOptions(
            stages_only=[
                PipelineStage.EXECUTIVE_RANKING,
                PipelineStage.VENTURE_REPORT,
            ],
            stop_on_failure=True,
        ),
    )

    assert result.status == PipelineRunStatus.COMPLETED
    assert result.stages_failed == 0
    assert result.stages_completed == 2

    detail = await orchestrator.get_run(result.pipeline_run_id)
    report_stage = next(
        stage for stage in detail.stage_runs if stage.stage == PipelineStage.VENTURE_REPORT
    )
    assert report_stage.status.value == "completed"
    assert report_stage.stage_metadata is not None
    assert "report_id" in report_stage.stage_metadata

    venture_service = VentureReportService(repos, pipeline_settings)
    content = await venture_service.get_report_content(report_stage.stage_metadata["report_id"])
    assert content.outcome == "empty_discovery"
    assert content.generated_count == 0
