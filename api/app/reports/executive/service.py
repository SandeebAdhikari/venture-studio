"""Executive report generation and persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.config import Settings, get_settings
from app.db.enums import ReportStatus, ReportType
from app.exceptions import NotFoundError, ValidationError
from app.logging import get_logger
from app.reports.executive.generator import ExecutiveReportGenerator
from app.reports.executive.schemas import (
    ExecutiveReportResult,
    KeyComplaintEntry,
    ReportMarkdownRead,
    TopOpportunityEntry,
)
from app.repositories import RepositoryContainer
from app.schemas.report import ReportCreate, ReportRead

logger = get_logger(__name__)


class ExecutiveReportService:
    """Generates Top Opportunities reports and stores them in the database."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        generator: ExecutiveReportGenerator | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._generator = generator or ExecutiveReportGenerator(
            key_complaints_limit=self._settings.executive_report_key_complaints_limit,
        )

    async def generate_top_opportunities_report(
        self,
        *,
        limit: int | None = None,
        publish: bool = True,
    ) -> ExecutiveReportResult:
        top_n = limit or self._settings.executive_report_top_n
        top_scores = await self._repos.opportunity_scores.list_top_by_score(limit=top_n)

        entries: list[TopOpportunityEntry] = []
        for score_row in top_scores:
            opportunity = await self._repos.opportunities.get_by_id_with_relations(
                score_row.opportunity_id
            )
            if opportunity is None:
                continue
            entries.append(self._build_entry(opportunity, score_row))

        generated_at = datetime.now(UTC)
        report_content = self._generator.build_report(entries, generated_at=generated_at)
        title = f"Top Opportunities Report — {generated_at.strftime('%Y-%m-%d')}"
        summary = f"{len(entries)} ranked opportunities by current score."

        entity = await self._repos.reports.create(
            ReportCreate(
                opportunity_id=None,
                report_type=ReportType.TOP_OPPORTUNITIES,
                title=title,
                summary=summary,
                content=report_content.model_dump(mode="json"),
                status=ReportStatus.PUBLISHED if publish else ReportStatus.DRAFT,
                report_metadata={
                    "engine": "executive_report_v1",
                    "generated_at": generated_at.isoformat(),
                    "top_n": top_n,
                    "opportunity_count": len(entries),
                },
            )
        )

        logger.info(
            "Top opportunities report generated",
            extra={"report_id": str(entity.id), "opportunity_count": len(entries)},
        )

        return ExecutiveReportResult(
            report_id=entity.id,
            title=entity.title,
            summary=entity.summary or summary,
            markdown=report_content.markdown,
            content=report_content,
        )

    async def get_report_markdown(self, report_id: UUID) -> ReportMarkdownRead:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)

        markdown = entity.content.get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            raise ValidationError(f"Report '{report_id}' does not contain markdown content")

        return ReportMarkdownRead(
            report_id=entity.id,
            title=entity.title,
            report_type=entity.report_type,
            markdown=markdown,
        )

    async def get_report(self, report_id: UUID) -> ReportRead:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)
        return ReportRead.model_validate(entity)

    def _build_entry(self, opportunity, score_row) -> TopOpportunityEntry:
        complaints = sorted(
            opportunity.complaints,
            key=lambda complaint: complaint.severity,
            reverse=True,
        )
        evidence = [self._complaint_entry(complaint) for complaint in complaints]
        key_complaints = evidence[: self._generator.key_complaints_limit]

        score = score_row.score
        confidence = opportunity.confidence_score

        return TopOpportunityEntry(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            score=score,
            confidence=confidence,
            recommendation=self._generator.recommend(score=score, confidence=confidence),
            supporting_evidence_count=len(evidence),
            supporting_evidence=evidence,
            key_complaints=key_complaints,
            problem_statement=opportunity.problem_statement,
            frequency_signal=opportunity.frequency_signal,
            gap=opportunity.gap,
        )

    @staticmethod
    def _complaint_entry(complaint) -> KeyComplaintEntry:
        source_url = None
        if complaint.signal is not None:
            source_url = complaint.signal.url
        return KeyComplaintEntry(
            id=complaint.id,
            summary=complaint.summary,
            verbatim_quote=complaint.verbatim_quote,
            severity=complaint.severity,
            source_url=source_url,
        )
