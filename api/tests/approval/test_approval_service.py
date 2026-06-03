"""Integration tests for approval service."""

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import ApprovalStatus, ApprovalSubjectType, ReportStatus
from app.exceptions import ValidationError
from app.ranking.service import ExecutiveRankingService
from app.reports.venture.service import VentureReportService
from app.repositories import get_repositories
from app.schemas.approval import ApprovalActionRequest
from app.services.approval import ApprovalService
from tests.ranking.test_executive_ranking_service import (
    AgentScoreProfile,
    _create_opportunity,
    _seed_agent_outputs,
)


@pytest.fixture
async def ranked_opportunity(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> UUID:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(
        db_session,
        taxonomy_ids,
        title="Approval Workflow SaaS",
    )
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, AgentScoreProfile())
    return opportunity.id


@pytest.mark.asyncio
async def test_executive_ranking_creates_pending_approval(
    db_session: AsyncSession,
    ranked_opportunity: UUID,
):
    repos = get_repositories(db_session)
    settings = Settings(api_key="approval-test-key", require_founder_approval=True)
    approval = ApprovalService(repos, settings)
    ranking_service = ExecutiveRankingService(repos, settings, approval_service=approval)

    result = await ranking_service.generate_ranking(top_n=5)
    assert result.ranked_opportunity_count >= 1

    approval_request = await repos.approval_requests.get_by_executive_ranking_run_id(
        result.ranking_run_id
    )
    assert approval_request is not None
    assert approval_request.status == ApprovalStatus.PENDING.value
    assert approval_request.subject_type == ApprovalSubjectType.EXECUTIVE_RANKING.value


@pytest.mark.asyncio
async def test_venture_report_creates_draft_and_pending_approval(
    db_session: AsyncSession,
    ranked_opportunity: UUID,
):
    repos = get_repositories(db_session)
    settings = Settings(api_key="approval-test-key", require_founder_approval=True)
    approval = ApprovalService(repos, settings)
    ranking_service = ExecutiveRankingService(repos, settings, approval_service=approval)
    await ranking_service.generate_ranking(top_n=5)

    venture_service = VentureReportService(
        repos,
        settings,
        ranking_service=ranking_service,
        approval_service=approval,
    )
    result = await venture_service.generate_venture_report(
        top_n=5, generate_ranking_if_missing=False
    )

    report = await repos.reports.get_by_id(result.report_id)
    assert report is not None
    assert report.status == ReportStatus.DRAFT.value

    approval_request = await repos.approval_requests.get_by_report_id(result.report_id)
    assert approval_request is not None
    assert approval_request.status == ApprovalStatus.PENDING.value


@pytest.mark.asyncio
async def test_approve_venture_report_publishes_and_records_history(
    db_session: AsyncSession,
    ranked_opportunity: UUID,
):
    repos = get_repositories(db_session)
    settings = Settings(api_key="approval-test-key", require_founder_approval=True)
    approval = ApprovalService(repos, settings)
    ranking_service = ExecutiveRankingService(repos, settings, approval_service=approval)
    await ranking_service.generate_ranking(top_n=5)
    venture_service = VentureReportService(
        repos,
        settings,
        ranking_service=ranking_service,
        approval_service=approval,
    )
    result = await venture_service.generate_venture_report(
        top_n=5, generate_ranking_if_missing=False
    )

    approval_request = await repos.approval_requests.get_by_report_id(result.report_id)
    assert approval_request is not None

    action = await approval.approve(
        approval_request.id,
        ApprovalActionRequest(comment="Looks good — proceed."),
    )
    assert action.status == ApprovalStatus.APPROVED
    assert action.finalized is True
    assert len(action.decision.comment or "") > 0

    report = await repos.reports.get_by_id(result.report_id)
    assert report is not None
    assert report.status == ReportStatus.PUBLISHED.value

    refreshed = await repos.approval_requests.get_by_id_with_decisions(approval_request.id)
    assert refreshed is not None
    assert len(refreshed.decisions) == 1
    assert len(refreshed.audit_trail) >= 2


@pytest.mark.asyncio
async def test_request_research_requires_comment(
    db_session: AsyncSession,
    ranked_opportunity: UUID,
):
    repos = get_repositories(db_session)
    settings = Settings(api_key="approval-test-key", require_founder_approval=True)
    approval = ApprovalService(repos, settings)
    ranking_service = ExecutiveRankingService(repos, settings, approval_service=approval)
    await ranking_service.generate_ranking(top_n=5)

    approval_request = await repos.approval_requests.get_by_executive_ranking_run_id(
        (await ranking_service.get_current_ranking()).id
    )
    assert approval_request is not None

    with pytest.raises(ValidationError, match="comment is required"):
        await approval.request_research(approval_request.id, ApprovalActionRequest())

    action = await approval.request_research(
        approval_request.id,
        ApprovalActionRequest(comment="Need deeper customer research on pricing."),
    )
    assert action.status == ApprovalStatus.RESEARCH_REQUESTED
