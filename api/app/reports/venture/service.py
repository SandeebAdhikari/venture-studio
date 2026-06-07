"""Orchestrates venture recommendation report generation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from app.config import Settings, get_settings
from app.db.enums import ReportStatus, ReportType
from app.discovery.validation import assert_ranking_bound_to_pipeline_run
from app.pipeline.lineage import merge_pipeline_run_lineage, pipeline_run_id_from_metadata
from app.exceptions import NotFoundError, ValidationError
from app.logging import get_logger
from app.ranking.service import ExecutiveRankingService
from app.reports.venture.collector import VentureReportCollector
from app.reports.venture.funnel import load_discovery_funnel
from app.reports.venture.generator import REPORT_ENGINE, VentureReportGenerator
from app.reports.venture.schemas import (
    VentureReportContent,
    VentureReportMarkdownRead,
    VentureReportRegenResult,
    VentureReportResult,
)
from app.schemas.human_proxy_evaluation import SCALE_VERSION_CENTURY_V1
from app.repositories import RepositoryContainer
from app.schemas.report import ReportCreate, ReportRead

if TYPE_CHECKING:
    from app.services.approval import ApprovalService

logger = get_logger(__name__)


class VentureReportService:
    """Generates complete venture recommendation reports for top-ranked opportunities."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        generator: VentureReportGenerator | None = None,
        ranking_service: ExecutiveRankingService | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._generator = generator or VentureReportGenerator()
        self._collector = VentureReportCollector(repos)
        self._approval = approval_service
        self._ranking_service = ranking_service or ExecutiveRankingService(
            repos,
            self._settings,
            approval_service=approval_service,
        )

    async def generate_venture_report(
        self,
        *,
        top_n: int | None = None,
        founder_profile_id: UUID | None = None,
        ranking_run_id: UUID | None = None,
        generate_ranking_if_missing: bool = True,
        discovery_validation_mode: bool = False,
        pipeline_run_id: UUID | None = None,
        publish: bool = True,
        report_metadata_extra: dict[str, object] | None = None,
    ) -> VentureReportResult:
        top_limit = top_n or self._settings.executive_venture_report_top_n

        if discovery_validation_mode:
            if ranking_run_id is None:
                raise ValidationError(
                    "Validation run requires ranking_run_id from the same pipeline run; "
                    "refusing stale current ranking"
                )
            generate_ranking_if_missing = False

        if ranking_run_id is not None:
            ranking = await self._ranking_service.get_ranking(ranking_run_id)
            if discovery_validation_mode:
                assert_ranking_bound_to_pipeline_run(
                    ranking_metadata=ranking.ranking_metadata or {},
                    pipeline_run_id=pipeline_run_id,
                )
        else:
            if discovery_validation_mode:
                raise ValidationError(
                    "Validation run cannot use current executive ranking (stale ranking risk)"
                )
            try:
                ranking = await self._ranking_service.get_current_ranking()
            except NotFoundError:
                if not generate_ranking_if_missing:
                    raise ValidationError(
                        "No executive ranking exists. Generate ranking first or set "
                        "generate_ranking_if_missing=true."
                    ) from None
                await self._ranking_service.generate_ranking(
                    top_n=top_limit,
                    founder_profile_id=founder_profile_id,
                )
                ranking = await self._ranking_service.get_current_ranking()

        top_entries = sorted(
            [entry for entry in ranking.entries if entry.is_top_opportunity],
            key=lambda item: item.rank,
        )[:top_limit]

        if not top_entries:
            top_entries = sorted(ranking.entries, key=lambda item: item.rank)[:top_limit]

        if not top_entries:
            top_entries = sorted(ranking.entries, key=lambda item: item.rank)[:top_limit]

        resolved_pipeline_run_id = pipeline_run_id or pipeline_run_id_from_metadata(
            ranking.ranking_metadata
        )

        profile_id = founder_profile_id or ranking.founder_profile_id
        generated_at = datetime.now(UTC)

        if not top_entries:
            discovery_funnel = await load_discovery_funnel(
                self._repos,
                pipeline_run_id=resolved_pipeline_run_id,
                ranked_opportunity_count=ranking.ranked_opportunity_count,
            )
            content = self._generator.build_report(
                [],
                generated_at=generated_at,
                executive_ranking_run_id=ranking.id,
                founder_profile_id=profile_id,
                discovery_funnel=discovery_funnel,
            )
            title = f"Venture Discovery Report — {generated_at.strftime('%Y-%m-%d')}"
            summary = (
                "Discovery completed with no founder-grade ranked opportunities. "
                f"Funnel: {discovery_funnel.signals_collected} signals, "
                f"{discovery_funnel.complaints_extracted} complaints, "
                f"{discovery_funnel.patterns_found} patterns, "
                f"{discovery_funnel.opportunities_generated} opportunities."
            )
            report_metadata = merge_pipeline_run_lineage(
                {
                    "engine": REPORT_ENGINE,
                    "generated_at": generated_at.isoformat(),
                    "executive_ranking_run_id": str(ranking.id),
                    "executive_ranking_version": ranking.version,
                    "founder_profile_id": str(profile_id) if profile_id else None,
                    "top_n": top_limit,
                    "opportunity_count": 0,
                    "outcome": "empty_discovery",
                    "discovery_funnel": discovery_funnel.model_dump(mode="json"),
                    **(
                        {"discovery_validation_mode": True}
                        if discovery_validation_mode
                        else {}
                    ),
                },
                pipeline_run_id=resolved_pipeline_run_id,
            )
            if report_metadata_extra:
                report_metadata.update(report_metadata_extra)
            if self._approval is not None and self._approval.enabled:
                publish = False

            entity = await self._repos.reports.create(
                ReportCreate(
                    opportunity_id=None,
                    report_type=ReportType.VENTURE_RECOMMENDATION,
                    title=title,
                    summary=summary,
                    content=content.model_dump(mode="json"),
                    status=ReportStatus.PUBLISHED if publish else ReportStatus.DRAFT,
                    report_metadata=report_metadata,
                )
            )

            logger.info(
                "Empty-discovery venture report generated",
                extra={
                    "report_id": str(entity.id),
                    "opportunity_count": 0,
                    "patterns_found": discovery_funnel.patterns_found,
                },
            )

            return VentureReportResult(
                report_id=entity.id,
                title=entity.title,
                summary=entity.summary or summary,
                markdown=content.markdown,
                content=content,
            )

        opportunity_reports = []
        for entry in top_entries:
            opportunity_reports.append(
                await self._collector.collect_opportunity(
                    entry,
                    founder_profile_id=profile_id,
                )
            )

        content = self._generator.build_report(
            opportunity_reports,
            generated_at=generated_at,
            executive_ranking_run_id=ranking.id,
            founder_profile_id=profile_id,
        )

        title = f"Venture Recommendation Report — {generated_at.strftime('%Y-%m-%d')}"
        summary = (
            f"Top {len(opportunity_reports)} opportunities with full venture analysis "
            f"for founder decision-making."
        )

        if self._approval is not None and self._approval.enabled:
            publish = False

        entity = await self._repos.reports.create(
            ReportCreate(
                opportunity_id=None,
                report_type=ReportType.VENTURE_RECOMMENDATION,
                title=title,
                summary=summary,
                content=content.model_dump(mode="json"),
                status=ReportStatus.PUBLISHED if publish else ReportStatus.DRAFT,
                report_metadata=merge_pipeline_run_lineage(
                    {
                        "engine": REPORT_ENGINE,
                        "generated_at": generated_at.isoformat(),
                        "executive_ranking_run_id": str(ranking.id),
                        "executive_ranking_version": ranking.version,
                        "founder_profile_id": str(profile_id) if profile_id else None,
                        "top_n": top_limit,
                        "opportunity_count": len(opportunity_reports),
                        **(
                            {"discovery_validation_mode": True}
                            if discovery_validation_mode
                            else {}
                        ),
                        **(report_metadata_extra or {}),
                    },
                    pipeline_run_id=resolved_pipeline_run_id,
                ),
            )
        )

        logger.info(
            "Venture recommendation report generated",
            extra={"report_id": str(entity.id), "opportunity_count": len(opportunity_reports)},
        )

        if self._approval is not None:
            await self._approval.create_for_venture_report(
                report_id=entity.id,
                title=entity.title,
                executive_ranking_run_id=ranking.id,
            )

        return VentureReportResult(
            report_id=entity.id,
            title=entity.title,
            summary=entity.summary or summary,
            markdown=content.markdown,
            content=content,
        )

    async def regenerate_current_reports(
        self,
        *,
        top_n: int | None = None,
        founder_profile_id: UUID | None = None,
        dry_run: bool = False,
        publish: bool = True,
    ) -> VentureReportRegenResult:
        """Regenerate the venture recommendation report from current ranking and agents.

        Inserts a new report row; prior reports remain queryable. The newest published
        report becomes the effective current report for dashboard and /latest.
        """
        top_limit = top_n or self._settings.executive_venture_report_top_n

        ranking = await self._ranking_service.get_current_ranking()
        profile_id = founder_profile_id or ranking.founder_profile_id
        opportunities_found = self._count_ranked_opportunities(ranking, top_limit=top_limit)

        venture_reports = await self._repos.reports.list_by_type(
            ReportType.VENTURE_RECOMMENDATION,
            limit=1000,
        )
        stale_reports_found = self._count_stale_reports(venture_reports, ranking.id)

        century_v1_hp_count = 0
        if profile_id is not None:
            century_evaluations = (
                await self._repos.human_proxy_evaluations.list_current_evaluations(
                    founder_profile_id=profile_id,
                    scale_version=SCALE_VERSION_CENTURY_V1,
                )
            )
            century_v1_hp_count = len(century_evaluations)

        latest_report_id: UUID | None = None
        try:
            latest_report_id = (await self.get_latest_report()).id
        except NotFoundError:
            pass

        result = VentureReportRegenResult(
            dry_run=dry_run,
            founder_profile_id=profile_id,
            top_n=top_limit,
            opportunities_found=opportunities_found,
            current_reports_found=len(venture_reports),
            stale_reports_found=stale_reports_found,
            current_ranking_run_id=ranking.id,
            current_ranking_version=ranking.version,
            century_v1_hp_count=century_v1_hp_count,
            superseded_report_id=latest_report_id,
        )

        if dry_run:
            logger.info(
                "Venture report regeneration dry run",
                extra={
                    "founder_profile_id": str(profile_id) if profile_id else None,
                    "opportunities_found": opportunities_found,
                    "current_reports_found": len(venture_reports),
                    "stale_reports_found": stale_reports_found,
                    "current_ranking_run_id": str(ranking.id),
                    "century_v1_hp_count": century_v1_hp_count,
                },
            )
            return result

        metadata_extra: dict[str, object] = {"regen": "report_regen_1"}
        if latest_report_id is not None:
            metadata_extra["supersedes_report_id"] = str(latest_report_id)

        report_result = await self.generate_venture_report(
            top_n=top_limit,
            founder_profile_id=profile_id,
            ranking_run_id=ranking.id,
            generate_ranking_if_missing=False,
            publish=publish,
            report_metadata_extra=metadata_extra,
        )

        result.report_id = report_result.report_id
        result.title = report_result.title
        result.summary = report_result.summary
        result.opportunity_count = report_result.content.generated_count

        logger.info(
            "Venture report regeneration complete",
            extra={
                "report_id": str(result.report_id),
                "opportunity_count": result.opportunity_count,
                "current_ranking_run_id": str(ranking.id),
                "superseded_report_id": (
                    str(result.superseded_report_id) if result.superseded_report_id else None
                ),
            },
        )
        return result

    @staticmethod
    def _count_ranked_opportunities(ranking, *, top_limit: int) -> int:
        top_entries = sorted(
            [entry for entry in ranking.entries if entry.is_top_opportunity],
            key=lambda item: item.rank,
        )[:top_limit]
        if not top_entries:
            top_entries = sorted(ranking.entries, key=lambda item: item.rank)[:top_limit]
        return len(top_entries)

    @staticmethod
    def _count_stale_reports(reports, current_ranking_run_id: UUID) -> int:
        stale = 0
        for report in reports:
            metadata = report.report_metadata or {}
            pinned = metadata.get("executive_ranking_run_id")
            if pinned is None or str(pinned) != str(current_ranking_run_id):
                stale += 1
        return stale

    async def get_latest_report(self) -> ReportRead:
        items = await self._repos.reports.list_by_type(
            ReportType.VENTURE_RECOMMENDATION,
            status=ReportStatus.PUBLISHED,
            limit=1,
        )
        if not items:
            items = await self._repos.reports.list_by_type(
                ReportType.VENTURE_RECOMMENDATION,
                limit=1,
            )
        if not items:
            raise NotFoundError("report", "latest")
        return ReportRead.model_validate(items[0])

    async def get_report(self, report_id: UUID) -> ReportRead:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)
        if entity.report_type != ReportType.VENTURE_RECOMMENDATION.value:
            raise ValidationError(f"Report '{report_id}' is not a venture recommendation report.")
        return ReportRead.model_validate(entity)

    async def get_report_content(self, report_id: UUID) -> VentureReportContent:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)
        if entity.report_type != ReportType.VENTURE_RECOMMENDATION.value:
            raise ValidationError(f"Report '{report_id}' is not a venture recommendation report.")
        return VentureReportContent.model_validate(entity.content)

    async def get_report_markdown(self, report_id: UUID) -> VentureReportMarkdownRead:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)

        markdown = entity.content.get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            raise ValidationError(f"Report '{report_id}' does not contain markdown content.")

        return VentureReportMarkdownRead(
            report_id=entity.id,
            title=entity.title,
            report_type=entity.report_type,
            markdown=markdown,
        )

    async def get_download_filename(self, report_id: UUID) -> tuple[str, str]:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)

        markdown_read = await self.get_report_markdown(report_id)
        safe_date = entity.created_at.strftime("%Y-%m-%d")
        filename = f"venture-recommendation-{safe_date}-{report_id.hex[:8]}.md"
        return filename, markdown_read.markdown
