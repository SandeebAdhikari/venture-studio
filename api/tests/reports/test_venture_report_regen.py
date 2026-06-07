"""Tests for VENTURE-REPORT-REGEN-1 venture report regeneration."""

from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ReportType
from app.db.models.report import Report
from app.ranking.service import ExecutiveRankingService
from app.reports.venture.service import VentureReportService
from app.repositories import get_repositories
from app.schemas.human_proxy_evaluation import SCALE_VERSION_CENTURY_V1
from tests.ranking.test_executive_ranking_service import (
    AgentScoreProfile,
    _create_opportunity,
    _seed_agent_outputs,
)

pytest_plugins = ["tests.ranking.test_executive_ranking_service"]


async def _seed_century_v1_hp(
    repos,
    opportunity_id: UUID,
    founder_profile_id: UUID,
    profile: AgentScoreProfile,
) -> None:
    from app.db.enums import HumanProxyEvaluationStatus
    from app.schemas.human_proxy_evaluation import HumanProxyEvaluationCreate

    await repos.human_proxy_evaluations.create(
        HumanProxyEvaluationCreate(
            opportunity_id=opportunity_id,
            founder_profile_id=founder_profile_id,
            status=HumanProxyEvaluationStatus.COMPLETED,
            founder_fit_score=profile.founder_fit,
            feasibility_score=profile.feasibility,
            recommendation="pursue",
            evaluation_metrics={
                "ranking_score": int(round(profile.founder_fit * 0.7 + profile.feasibility * 0.3))
            },
            llm_model="mock-human-proxy",
            scale_version=SCALE_VERSION_CENTURY_V1,
            scale_metadata={"scale_detected": "century"},
        )
    )


@pytest.mark.asyncio
async def test_regenerate_current_reports_dry_run_does_not_create_report(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Dry Run Venture")
    profile = AgentScoreProfile(founder_fit=82, feasibility=78)
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, profile)

    ranking_service = ExecutiveRankingService(repos)
    venture_service = VentureReportService(repos, ranking_service=ranking_service)
    await ranking_service.generate_ranking(top_n=5)
    await venture_service.generate_venture_report(top_n=5, generate_ranking_if_missing=False)

    before = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )
    result = await venture_service.regenerate_current_reports(dry_run=True)

    after = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )
    assert after == before
    assert result.dry_run is True
    assert result.opportunities_found >= 1
    assert result.current_reports_found >= 1
    assert result.current_ranking_run_id is not None
    assert result.report_id is None


@pytest.mark.asyncio
async def test_regenerate_current_reports_pins_current_ranking_and_preserves_history(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Regen Venture")
    profile = AgentScoreProfile(founder_fit=85, feasibility=80)
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, profile)

    ranking_service = ExecutiveRankingService(repos)
    venture_service = VentureReportService(repos, ranking_service=ranking_service)
    ranking = await ranking_service.generate_ranking(top_n=5)
    first = await venture_service.generate_venture_report(
        top_n=5,
        generate_ranking_if_missing=False,
    )

    first_report = await repos.reports.get_by_id(first.report_id)
    assert first_report is not None
    first_report.report_metadata = {
        **(first_report.report_metadata or {}),
        "executive_ranking_run_id": "00000000-0000-0000-0000-000000000001",
    }
    await db_session.flush()

    reports_before = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )
    result = await venture_service.regenerate_current_reports(top_n=5)

    reports_after = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )
    assert reports_after == reports_before + 1
    assert result.report_id is not None
    assert result.report_id != first.report_id
    assert result.stale_reports_found >= 1

    new_report = await repos.reports.get_by_id(result.report_id)
    assert new_report is not None
    assert new_report.report_metadata["regen"] == "report_regen_1"
    assert new_report.report_metadata["executive_ranking_run_id"] == str(ranking.ranking_run_id)
    assert new_report.report_metadata["supersedes_report_id"] == str(first.report_id)
    assert new_report.content["executive_ranking_run_id"] == str(ranking.ranking_run_id)

    loaded = await venture_service.get_report(result.report_id)
    assert loaded.id == result.report_id
    assert loaded.report_metadata["regen"] == "report_regen_1"


@pytest.mark.asyncio
async def test_regenerate_current_reports_is_idempotent_via_append_only_history(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Idempotent Venture")
    profile = AgentScoreProfile()
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, profile)

    ranking_service = ExecutiveRankingService(repos)
    venture_service = VentureReportService(repos, ranking_service=ranking_service)
    reports_before = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )
    await ranking_service.generate_ranking(top_n=5)
    first = await venture_service.regenerate_current_reports(top_n=5)
    second = await venture_service.regenerate_current_reports(top_n=5)
    reports_after = await db_session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.report_type == ReportType.VENTURE_RECOMMENDATION.value)
    )

    assert first.report_id is not None
    assert second.report_id is not None
    assert second.report_id != first.report_id
    assert reports_after == reports_before + 2
