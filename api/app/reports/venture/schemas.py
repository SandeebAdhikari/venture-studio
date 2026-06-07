"""Schemas for venture recommendation reports."""

from uuid import UUID

from pydantic import BaseModel, Field


class CustomerEvidenceItem(BaseModel):
    summary: str
    verbatim_quote: str
    severity: int = Field(ge=1, le=5)
    source_url: str | None = None


class RiskItem(BaseModel):
    category: str
    severity: str
    description: str


class VentureOpportunityReport(BaseModel):
    rank: int
    opportunity_id: UUID
    title: str
    final_opportunity_score: int = Field(ge=0, le=100)
    pain_score: int | None = None
    market_score: int | None = None
    revenue_score: int | None = None
    competition_score: int | None = None
    growth_score: int | None = None
    founder_fit_score: int | None = None

    opportunity_summary: str
    market_analysis: str
    competitor_analysis: str
    customer_evidence: list[CustomerEvidenceItem] = Field(default_factory=list)
    revenue_analysis: str
    mvp_plan: str
    go_to_market_strategy: str
    growth_strategy: str
    founder_fit_analysis: str
    risk_analysis: list[RiskItem] = Field(default_factory=list)
    recommendation: str


class VentureDiscoveryFunnelSummary(BaseModel):
    signals_collected: int = 0
    complaints_extracted: int = 0
    patterns_found: int = 0
    opportunities_generated: int = 0
    ranked_opportunity_count: int = 0


class VentureReportContent(BaseModel):
    format: str = "markdown"
    markdown: str
    executive_ranking_run_id: UUID | None = None
    founder_profile_id: UUID | None = None
    opportunities: list[VentureOpportunityReport] = Field(default_factory=list)
    generated_count: int = 0
    outcome: str = "ranked_opportunities"
    discovery_funnel: VentureDiscoveryFunnelSummary | None = None


class VentureReportResult(BaseModel):
    report_id: UUID
    title: str
    summary: str
    markdown: str
    content: VentureReportContent


class VentureReportRegenResult(BaseModel):
    """Outcome for VENTURE-REPORT-REGEN-1 post-ranking venture report refresh."""

    dry_run: bool = False
    founder_profile_id: UUID | None = None
    top_n: int = 0
    opportunities_found: int = 0
    current_reports_found: int = 0
    stale_reports_found: int = 0
    current_ranking_run_id: UUID | None = None
    current_ranking_version: int | None = None
    century_v1_hp_count: int = 0
    superseded_report_id: UUID | None = None
    report_id: UUID | None = None
    title: str | None = None
    summary: str | None = None
    opportunity_count: int = 0


class VentureReportMarkdownRead(BaseModel):
    report_id: UUID
    title: str
    report_type: str
    markdown: str
