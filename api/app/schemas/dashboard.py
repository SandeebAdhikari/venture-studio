"""Dashboard response schemas optimized for Next.js consumption."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import (
    PipelineRunStatus,
    PipelineStage,
    PipelineStageStatus,
    PipelineTrigger,
    ReportStatus,
    ReportType,
    ReviewStatus,
)
from app.schemas.pagination import PaginatedResponse


class DashboardReportSummary(BaseModel):
    id: UUID
    report_type: ReportType
    title: str
    summary: str | None = None
    status: ReportStatus
    opportunity_id: UUID | None = None
    created_at: datetime
    report_metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardPipelineRunSummary(BaseModel):
    id: UUID
    trigger: PipelineTrigger
    status: PipelineRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    stages_completed: int = 0
    stages_failed: int = 0
    stages_skipped: int = 0
    error_summary: str | None = None


class DashboardPipelineStageSummary(BaseModel):
    stage: PipelineStage
    sequence: int
    status: PipelineStageStatus
    duration_ms: int | None = None
    items_in: int = 0
    items_out: int = 0
    items_failed: int = 0
    records_processed: int = 0
    error_detail: str | None = None


class DashboardPipelineDetail(BaseModel):
    run: DashboardPipelineRunSummary
    stage_runs: list[DashboardPipelineStageSummary] = Field(default_factory=list)


class DashboardCollectionMetrics(BaseModel):
    signals_total: int = 0
    signals_pending: int = 0
    signals_classified: int = 0
    signals_failed: int = 0
    signals_skipped: int = 0
    complaints_total: int = 0
    sources_enabled: int = 0


class DashboardClassificationMetrics(BaseModel):
    signals_pending: int = 0
    signals_classified: int = 0
    signals_failed: int = 0
    signals_skipped: int = 0
    complaints_total: int = 0
    llm_calls_total: int = 0
    llm_cost_usd_total: float = 0.0


class DashboardAgentStatus(BaseModel):
    agent: str
    display_name: str
    current_completed: int = 0
    current_failed: int = 0
    current_skipped: int = 0
    current_total: int = 0


class DashboardResearchMetrics(BaseModel):
    opportunities_total: int = 0
    agents: list[DashboardAgentStatus] = Field(default_factory=list)
    average_agent_coverage: float | None = None


class DashboardRankingSummary(BaseModel):
    current_run_id: UUID | None = None
    version: int | None = None
    top_n: int | None = None
    ranked_opportunity_count: int = 0
    generated_at: datetime | None = None


class DashboardJobSummary(BaseModel):
    job_id: str
    job_name: str
    status: str
    finished_at: datetime | None = None


class DashboardSchedulerSummary(BaseModel):
    job_name: str
    enabled: bool
    schedule_cron: str
    last_run_status: str | None = None
    failure_count: int = 0


class DashboardOpportunityItem(BaseModel):
    rank: int | None = None
    opportunity_id: UUID
    title: str
    review_status: ReviewStatus
    confidence_score: float
    final_opportunity_score: int | None = None
    pain_score: int | None = None
    market_score: int | None = None
    revenue_score: int | None = None
    competition_score: int | None = None
    growth_score: int | None = None
    founder_fit_score: int | None = None
    agent_coverage_count: int | None = None
    score: int | None = None
    is_top_opportunity: bool = False


class DashboardOpportunitiesResponse(BaseModel):
    source: Literal["executive_ranking", "opportunity_score"]
    ranking_run_id: UUID | None = None
    version: int | None = None
    top_n: int
    ranked_opportunity_count: int = 0
    total_opportunities: int = 0
    items: list[DashboardOpportunityItem] = Field(default_factory=list)
    executive_rankings: list[DashboardOpportunityItem] = Field(default_factory=list)


class DashboardPipelineResponse(BaseModel):
    running: DashboardPipelineRunSummary | None = None
    runs: PaginatedResponse[DashboardPipelineRunSummary]
    latest_detail: DashboardPipelineDetail | None = None
    stage_order: list[PipelineStage] = Field(default_factory=list)


class DashboardReportsResponse(BaseModel):
    featured_venture_report: DashboardReportSummary | None = None
    venture_reports: list[DashboardReportSummary] = Field(default_factory=list)
    top_opportunity_reports: list[DashboardReportSummary] = Field(default_factory=list)
    pipeline_reports: list[DashboardReportSummary] = Field(default_factory=list)
    total_by_type: dict[str, int] = Field(default_factory=dict)


class DashboardSummaryResponse(BaseModel):
    generated_at: datetime
    pipeline: dict[str, DashboardPipelineRunSummary | None]
    collection: DashboardCollectionMetrics
    classification: DashboardClassificationMetrics
    research: DashboardResearchMetrics
    opportunities: dict[str, Any]
    ranking: DashboardRankingSummary
    reports: dict[str, DashboardReportSummary | None]
    agents: list[DashboardAgentStatus]
    background: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
