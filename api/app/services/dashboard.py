"""Dashboard aggregation service for Next.js consumption."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.config import Settings, get_settings
from app.db.enums import ReportStatus, ReportType, ReviewStatus
from app.pipeline.constants import PIPELINE_STAGE_ORDER
from app.repositories import RepositoryContainer
from app.repositories.dashboard import DashboardMetricsRepository
from app.schemas.dashboard import (
    DashboardAgentStatus,
    DashboardClassificationMetrics,
    DashboardCollectionMetrics,
    DashboardJobSummary,
    DashboardOpportunitiesResponse,
    DashboardOpportunityItem,
    DashboardPipelineDetail,
    DashboardPipelineResponse,
    DashboardPipelineRunSummary,
    DashboardPipelineStageSummary,
    DashboardRankingSummary,
    DashboardReportsResponse,
    DashboardReportSummary,
    DashboardResearchMetrics,
    DashboardSchedulerSummary,
    DashboardSummaryResponse,
)
from app.schemas.filters import ReportListFilter
from app.schemas.pagination import PaginatedResponse
from app.schemas.pipeline import PipelineRunRead, PipelineStageRunRead

if TYPE_CHECKING:
    pass


class DashboardService:
    def __init__(self, repos: RepositoryContainer, settings: Settings | None = None) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._metrics = DashboardMetricsRepository(repos.session)

    async def get_summary(
        self,
        *,
        recent_jobs: list[DashboardJobSummary] | None = None,
        scheduler_jobs: list[DashboardSchedulerSummary] | None = None,
    ) -> DashboardSummaryResponse:
        running = await self._repos.pipelines.get_running()
        latest_runs = await self._repos.pipelines.list_runs(limit=1)
        latest_run = latest_runs[0] if latest_runs else None

        collection_raw = await self._metrics.collection_metrics()
        classification_raw = await self._metrics.classification_metrics()
        research_raw = await self._metrics.research_metrics()
        review_counts = self._metrics.review_status_map(
            await self._metrics.count_opportunities_by_review_status()
        )

        ranking = await self._repos.executive_rankings.get_current()
        venture_reports = await self._repos.reports.list_by_type(
            ReportType.VENTURE_RECOMMENDATION,
            status=ReportStatus.PUBLISHED,
            limit=1,
        )

        agents = [DashboardAgentStatus.model_validate(item) for item in research_raw["agents"]]

        return DashboardSummaryResponse(
            generated_at=datetime.now(UTC),
            pipeline={
                "running": self._pipeline_run_summary(running),
                "latest": self._pipeline_run_summary(latest_run),
            },
            collection=DashboardCollectionMetrics.model_validate(collection_raw),
            classification=DashboardClassificationMetrics(
                signals_pending=collection_raw["signals_pending"],
                signals_classified=classification_raw["classified"],
                signals_failed=classification_raw["failed"],
                signals_skipped=classification_raw["skipped"],
                complaints_total=classification_raw["complaints_total"],
                llm_calls_total=classification_raw["calls_total"],
                llm_cost_usd_total=classification_raw["cost_usd_total"],
            ),
            research=DashboardResearchMetrics(
                opportunities_total=research_raw["opportunities_total"],
                agents=agents,
                average_agent_coverage=research_raw["average_agent_coverage"],
            ),
            opportunities={
                "total": research_raw["opportunities_total"],
                "by_review_status": review_counts,
            },
            ranking=DashboardRankingSummary(
                current_run_id=ranking.id if ranking else None,
                version=ranking.version if ranking else None,
                top_n=ranking.top_n if ranking else None,
                ranked_opportunity_count=ranking.ranked_opportunity_count if ranking else 0,
                generated_at=ranking.created_at if ranking else None,
            ),
            reports={
                "latest_venture": self._report_summary(venture_reports[0])
                if venture_reports
                else None,
            },
            agents=agents,
            background={
                "recent_jobs": recent_jobs or [],
                "scheduler_jobs": scheduler_jobs or [],
            },
        )

    async def get_opportunities(
        self, *, top_n: int | None = None
    ) -> DashboardOpportunitiesResponse:
        limit = top_n or self._settings.executive_ranking_top_n
        total = await self._metrics.count_opportunities()

        ranking = await self._repos.executive_rankings.get_current_with_entries()
        if ranking is not None:
            top_entries = sorted(
                [entry for entry in ranking.entries if entry.is_top_opportunity],
                key=lambda entry: entry.rank,
            )[:limit]
            opportunity_ids = [entry.opportunity_id for entry in top_entries]
            opportunities = await self._load_opportunities_by_ids(opportunity_ids)
            items = [
                self._ranking_opportunity_item(entry, opportunities.get(entry.opportunity_id))
                for entry in top_entries
            ]
            all_ranked = sorted(ranking.entries, key=lambda entry: entry.rank)
            executive_rankings = [
                self._ranking_opportunity_item(entry, opportunities.get(entry.opportunity_id))
                for entry in all_ranked
            ]
            return DashboardOpportunitiesResponse(
                source="executive_ranking",
                ranking_run_id=ranking.id,
                version=ranking.version,
                top_n=limit,
                ranked_opportunity_count=ranking.ranked_opportunity_count,
                total_opportunities=total,
                items=items,
                executive_rankings=executive_rankings,
            )

        scores = await self._repos.opportunity_scores.list_top_by_score(limit=limit)
        items: list[DashboardOpportunityItem] = []
        for index, score in enumerate(scores, start=1):
            opportunity = await self._repos.opportunities.get_by_id(score.opportunity_id)
            if opportunity is None:
                continue
            items.append(
                DashboardOpportunityItem(
                    rank=index,
                    opportunity_id=opportunity.id,
                    title=opportunity.title,
                    review_status=ReviewStatus(opportunity.review_status),
                    confidence_score=opportunity.confidence_score,
                    score=score.score,
                    is_top_opportunity=True,
                )
            )
        return DashboardOpportunitiesResponse(
            source="opportunity_score",
            top_n=limit,
            total_opportunities=total,
            items=items,
            executive_rankings=items,
        )

    async def get_pipeline(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
        include_stages: bool = True,
    ) -> DashboardPipelineResponse:
        running = await self._repos.pipelines.get_running()
        runs = await self._repos.pipelines.list_runs(limit=limit, offset=offset)
        total = await self._repos.pipelines.count_runs()

        latest_detail = None
        if include_stages:
            detail_run = running or (runs[0] if runs else None)
            if detail_run is not None:
                full_run = await self._repos.pipelines.get_by_id_with_stages(detail_run.id)
                if full_run is not None:
                    stage_runs = sorted(full_run.stage_runs, key=lambda stage: stage.sequence)
                    latest_detail = DashboardPipelineDetail(
                        run=self._pipeline_run_summary(full_run),
                        stage_runs=[self._pipeline_stage_summary(stage) for stage in stage_runs],
                    )

        return DashboardPipelineResponse(
            running=self._pipeline_run_summary(running),
            runs=PaginatedResponse[DashboardPipelineRunSummary](
                items=[self._pipeline_run_summary(run) for run in runs],
                total=total,
                limit=limit,
                offset=offset,
            ),
            latest_detail=latest_detail,
            stage_order=list(PIPELINE_STAGE_ORDER),
        )

    async def get_reports(self, *, limit: int = 5) -> DashboardReportsResponse:
        venture = await self._repos.reports.list_by_type(
            ReportType.VENTURE_RECOMMENDATION,
            limit=limit,
        )
        top_opportunities = await self._repos.reports.list_by_type(
            ReportType.TOP_OPPORTUNITIES,
            limit=limit,
        )
        pipeline_reports = await self._repos.reports.list_by_type(
            ReportType.PIPELINE_SUMMARY,
            limit=limit,
        )

        featured = venture[0] if venture else None
        total_by_type = {
            ReportType.VENTURE_RECOMMENDATION.value: await self._repos.reports.count_filtered(
                ReportListFilter(report_type=ReportType.VENTURE_RECOMMENDATION)
            ),
            ReportType.TOP_OPPORTUNITIES.value: await self._repos.reports.count_filtered(
                ReportListFilter(report_type=ReportType.TOP_OPPORTUNITIES)
            ),
            ReportType.PIPELINE_SUMMARY.value: await self._repos.reports.count_filtered(
                ReportListFilter(report_type=ReportType.PIPELINE_SUMMARY)
            ),
        }

        return DashboardReportsResponse(
            featured_venture_report=self._report_summary(featured) if featured else None,
            venture_reports=[self._report_summary(report) for report in venture],
            top_opportunity_reports=[self._report_summary(report) for report in top_opportunities],
            pipeline_reports=[self._report_summary(report) for report in pipeline_reports],
            total_by_type=total_by_type,
        )

    async def _load_opportunities_by_ids(self, ids: list[UUID]) -> dict[UUID, Any]:
        if not ids:
            return {}
        from sqlalchemy import select

        from app.db.models.opportunity import Opportunity

        result = await self._repos.session.execute(
            select(Opportunity).where(Opportunity.id.in_(ids))
        )
        return {opportunity.id: opportunity for opportunity in result.scalars().all()}

    @staticmethod
    def _pipeline_run_summary(run) -> DashboardPipelineRunSummary | None:
        if run is None:
            return None
        read = PipelineRunRead.from_entity(run)
        return DashboardPipelineRunSummary(
            id=read.id,
            trigger=read.trigger,
            status=read.status,
            started_at=read.started_at,
            finished_at=read.finished_at,
            duration_ms=read.duration_ms,
            stages_completed=read.stages_completed,
            stages_failed=read.stages_failed,
            stages_skipped=read.stages_skipped,
            error_summary=read.error_summary,
        )

    @staticmethod
    def _pipeline_stage_summary(stage_run) -> DashboardPipelineStageSummary:
        read = PipelineStageRunRead.from_entity(stage_run)
        return DashboardPipelineStageSummary(
            stage=read.stage,
            sequence=read.sequence,
            status=read.status,
            duration_ms=read.duration_ms,
            items_in=read.items_in,
            items_out=read.items_out,
            items_failed=read.items_failed,
            records_processed=read.records_processed,
            error_detail=read.error_detail,
        )

    @staticmethod
    def _report_summary(report) -> DashboardReportSummary | None:
        if report is None:
            return None
        return DashboardReportSummary(
            id=report.id,
            report_type=ReportType(report.report_type),
            title=report.title,
            summary=report.summary,
            status=ReportStatus(report.status),
            opportunity_id=report.opportunity_id,
            created_at=report.created_at,
            report_metadata=report.report_metadata or {},
        )

    @staticmethod
    def _ranking_opportunity_item(entry, opportunity) -> DashboardOpportunityItem:
        title = (
            opportunity.title
            if opportunity is not None
            else entry.ranking_details.get(
                "opportunity_title",
                "Unknown opportunity",
            )
        )
        review_status = (
            ReviewStatus(opportunity.review_status) if opportunity is not None else ReviewStatus.NEW
        )
        confidence = opportunity.confidence_score if opportunity is not None else 0.0
        return DashboardOpportunityItem(
            rank=entry.rank,
            opportunity_id=entry.opportunity_id,
            title=title,
            review_status=review_status,
            confidence_score=confidence,
            final_opportunity_score=entry.final_opportunity_score,
            pain_score=entry.pain_score,
            market_score=entry.market_score,
            revenue_score=entry.revenue_score,
            competition_score=entry.competition_score,
            growth_score=entry.growth_score,
            founder_fit_score=entry.founder_fit_score,
            agent_coverage_count=entry.agent_coverage_count,
            is_top_opportunity=entry.is_top_opportunity,
        )
