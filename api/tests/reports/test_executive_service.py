"""Integration tests for executive report service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CategoryKind, ReportType, SourceType
from app.db.models.category import Category
from app.db.models.report import Report
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.reports.executive.service import ExecutiveReportService
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.opportunity import OpportunityCreate
from app.scoring.service import OpportunityScoringService


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
            Category.code == "devtools",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "founder",
        )
    )
    assert category is not None and domain is not None and persona is not None
    return category.id, domain.id, persona.id


async def _seed_scored_opportunity(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> UUID:
    category_id, domain_id, persona_id = taxonomy_ids
    repos = get_repositories(db_session)

    source = Source(
        name=f"report-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/scheduling-pain",
        title="Scheduling pain",
        body="Staff scheduling is broken for our team.",
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
            summary="Staff scheduling breaks when managers rebuild shifts manually.",
            verbatim_quote="Staff scheduling breaks when managers rebuild shifts manually.",
            severity=5,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )

    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Founders managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints in evidence.",
            existing_alternatives="ShiftApp and spreadsheets mentioned in complaints.",
            gap="No lightweight staff scheduling workflow for small teams.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    await OpportunityScoringService(repos).score_opportunity(opportunity.id)
    return opportunity.id


@pytest.mark.asyncio
async def test_generate_top_opportunities_report_persists_markdown(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    await _seed_scored_opportunity(db_session, taxonomy_ids)
    service = ExecutiveReportService(get_repositories(db_session))

    result = await service.generate_top_opportunities_report(limit=5)

    assert result.report_id is not None
    assert "Top Opportunities Report" in result.markdown
    assert "Staff Scheduling SaaS" in result.markdown
    assert result.content.generated_count >= 1
    assert result.content.opportunities[0].score >= 0

    stored = await db_session.scalar(select(Report).where(Report.id == result.report_id))
    assert stored is not None
    assert stored.report_type == ReportType.TOP_OPPORTUNITIES.value
    assert stored.content["markdown"] == result.markdown


@pytest.mark.asyncio
async def test_get_report_markdown(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    await _seed_scored_opportunity(db_session, taxonomy_ids)
    service = ExecutiveReportService(get_repositories(db_session))
    generated = await service.generate_top_opportunities_report(limit=5)

    markdown = await service.get_report_markdown(generated.report_id)

    assert markdown.report_id == generated.report_id
    assert markdown.markdown == generated.markdown
    assert markdown.report_type == ReportType.TOP_OPPORTUNITIES.value
