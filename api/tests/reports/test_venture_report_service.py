"""Integration tests for venture recommendation report service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CategoryKind, ReportType, SourceType
from app.db.models.report import Report
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.ranking.service import ExecutiveRankingService
from app.reports.venture.service import VentureReportService
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate
from tests.ranking.test_executive_ranking_service import (
    AgentScoreProfile,
    _seed_agent_outputs,
)


@pytest.fixture
async def taxonomy_ids(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    from app.db.models.category import Category

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
) -> UUID:
    category_id, domain_id, persona_id = taxonomy_ids
    repos = get_repositories(db_session)

    source = Source(
        name=f"venture-report-source-{uuid4()}",
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
            title="Staff Scheduling SaaS",
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
    return opportunity.id


@pytest.mark.asyncio
async def test_generate_venture_report_includes_all_sections(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity_id = await _create_opportunity(db_session, taxonomy_ids)
    await _seed_agent_outputs(repos, opportunity_id, default_profile.id, AgentScoreProfile())

    ranking_service = ExecutiveRankingService(repos)
    await ranking_service.generate_ranking(top_n=5)

    service = VentureReportService(repos, ranking_service=ranking_service)
    result = await service.generate_venture_report(top_n=5, generate_ranking_if_missing=False)

    assert result.content.generated_count >= 1
    assert "# Venture Recommendation Report" in result.markdown
    assert "### Market analysis" in result.markdown
    assert "### Founder fit analysis" in result.markdown
    assert "### Risk analysis" in result.markdown
    assert result.content.opportunities[0].final_opportunity_score > 0

    report = await db_session.scalar(select(Report).where(Report.id == result.report_id))
    assert report is not None
    assert report.report_type == ReportType.VENTURE_RECOMMENDATION.value


@pytest.mark.asyncio
async def test_get_report_markdown_and_download(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity_id = await _create_opportunity(db_session, taxonomy_ids)
    await _seed_agent_outputs(repos, opportunity_id, default_profile.id, AgentScoreProfile())

    ranking_service = ExecutiveRankingService(repos)
    await ranking_service.generate_ranking(top_n=5)

    service = VentureReportService(repos, ranking_service=ranking_service)
    result = await service.generate_venture_report(top_n=5, generate_ranking_if_missing=False)

    markdown = await service.get_report_markdown(result.report_id)
    assert markdown.report_type == ReportType.VENTURE_RECOMMENDATION.value
    assert "Staff Scheduling SaaS" in markdown.markdown

    filename, body = await service.get_download_filename(result.report_id)
    assert filename.endswith(".md")
    assert "Venture Recommendation Report" in body

    latest = await service.get_latest_report()
    assert latest.id == result.report_id
