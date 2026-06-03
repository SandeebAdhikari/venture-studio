"""Schemas for venture recommendation reports."""

from typing import Any
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


class VentureReportContent(BaseModel):
    format: str = "markdown"
    markdown: str
    executive_ranking_run_id: UUID | None = None
    founder_profile_id: UUID | None = None
    opportunities: list[VentureOpportunityReport] = Field(default_factory=list)
    generated_count: int = 0


class VentureReportResult(BaseModel):
    report_id: UUID
    title: str
    summary: str
    markdown: str
    content: VentureReportContent


class VentureReportMarkdownRead(BaseModel):
    report_id: UUID
    title: str
    report_type: str
    markdown: str
