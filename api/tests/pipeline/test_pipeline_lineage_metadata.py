"""Pipeline lineage via ranking_metadata and report_metadata (no migrations)."""

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
from app.pipeline.lineage import (
    PIPELINE_RUN_ID_METADATA_KEY,
    merge_pipeline_run_lineage,
    pipeline_run_id_from_metadata,
)
from app.pipeline.orchestrator import PipelineOrchestrator
from app.ranking.service import ExecutiveRankingService
from app.repositories import get_repositories
from app.reports.venture.service import VentureReportService
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
        api_key="test-pipeline-lineage-key",
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
        name=f"lineage-source-{uuid4()}",
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
            title=f"Lineage Pipeline SaaS {uuid4()}",
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


def test_merge_pipeline_run_lineage_adds_and_preserves_keys() -> None:
    run_id = uuid4()
    merged = merge_pipeline_run_lineage(
        {"founder_profile_name": "Default"},
        pipeline_run_id=run_id,
    )
    assert merged["founder_profile_name"] == "Default"
    assert merged[PIPELINE_RUN_ID_METADATA_KEY] == str(run_id)

    unchanged = merge_pipeline_run_lineage({"only": 1}, pipeline_run_id=None)
    assert PIPELINE_RUN_ID_METADATA_KEY not in unchanged


def test_pipeline_run_id_from_metadata_round_trip() -> None:
    run_id = uuid4()
    assert pipeline_run_id_from_metadata(
        {PIPELINE_RUN_ID_METADATA_KEY: str(run_id)}
    ) == run_id
    assert pipeline_run_id_from_metadata({}) is None


@pytest.mark.asyncio
async def test_ranking_stores_pipeline_run_id_without_validation_mode(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    pipeline_settings: Settings,
) -> None:
    await _seed_ranked_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    profile = await repos.founder_profiles.get_default()
    assert profile is not None

    pipeline_run_id = uuid4()
    ranking_service = ExecutiveRankingService(repos, pipeline_settings)
    result = await ranking_service.generate_ranking(
        founder_profile_id=profile.id,
        pipeline_run_id=pipeline_run_id,
    )

    loaded = await repos.executive_rankings.get_by_id_with_entries(result.ranking_run_id)
    assert loaded is not None
    assert loaded.ranking_metadata.get(PIPELINE_RUN_ID_METADATA_KEY) == str(
        pipeline_run_id
    )
    assert "discovery_validation_mode" not in loaded.ranking_metadata


@pytest.mark.asyncio
async def test_pipeline_run_ranking_venture_report_lineage_end_to_end(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    pipeline_settings: Settings,
) -> None:
    await _seed_ranked_opportunity(db_session, taxonomy_ids)

    repos = get_repositories(db_session)
    orchestrator = PipelineOrchestrator(repos, ServiceContainer(repos), pipeline_settings)
    run = await orchestrator.run_pipeline(
        options=PipelineRunOptions(
            stages_only=[
                PipelineStage.EXECUTIVE_RANKING,
                PipelineStage.VENTURE_REPORT,
            ],
            stop_on_failure=True,
        ),
    )

    assert run.stages_completed == 2
    assert run.stages_failed == 0

    pipeline_run_id = run.pipeline_run_id
    detail = await orchestrator.get_run(pipeline_run_id)

    ranking_stage = next(
        s for s in detail.stage_runs if s.stage == PipelineStage.EXECUTIVE_RANKING
    )
    report_stage = next(
        s for s in detail.stage_runs if s.stage == PipelineStage.VENTURE_REPORT
    )
    ranking_run_id = UUID(str(ranking_stage.stage_metadata["ranking_run_id"]))
    report_id = UUID(str(report_stage.stage_metadata["report_id"]))

    ranking = await repos.executive_rankings.get_by_id_with_entries(ranking_run_id)
    assert ranking is not None
    assert ranking.ranking_metadata.get(PIPELINE_RUN_ID_METADATA_KEY) == str(
        pipeline_run_id
    )

    report = await repos.reports.get_by_id(report_id)
    assert report is not None
    meta = report.report_metadata
    assert meta.get(PIPELINE_RUN_ID_METADATA_KEY) == str(pipeline_run_id)
    assert meta.get("executive_ranking_run_id") == str(ranking_run_id)

    report_count = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )
    assert report_count >= 1


@pytest.mark.asyncio
async def test_venture_report_inherits_pipeline_run_id_from_ranking_metadata(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    pipeline_settings: Settings,
) -> None:
    await _seed_ranked_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    profile = await repos.founder_profiles.get_default()
    assert profile is not None

    pipeline_run_id = uuid4()
    ranking_service = ExecutiveRankingService(repos, pipeline_settings)
    ranking_result = await ranking_service.generate_ranking(
        founder_profile_id=profile.id,
        pipeline_run_id=pipeline_run_id,
    )

    venture_service = VentureReportService(repos, pipeline_settings)
    report_result = await venture_service.generate_venture_report(
        ranking_run_id=ranking_result.ranking_run_id,
        founder_profile_id=profile.id,
        generate_ranking_if_missing=False,
        publish=False,
    )

    report = await repos.reports.get_by_id(report_result.report_id)
    assert report is not None
    assert report.report_metadata.get(PIPELINE_RUN_ID_METADATA_KEY) == str(
        pipeline_run_id
    )
