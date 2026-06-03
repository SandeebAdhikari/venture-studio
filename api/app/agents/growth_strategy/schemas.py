"""Schemas for the growth strategy agent."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ComplaintEvidenceItem(BaseModel):
    index: int
    complaint_id: UUID
    signal_id: UUID
    summary: str
    verbatim_quote: str
    severity: int = Field(ge=1, le=5)
    product_mentions: list[str] = Field(default_factory=list)


class SEOPotentialOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    keyword_themes: list[str] = Field(min_length=1)
    content_momentum: str
    rationale: str


class ReferralPotentialOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    referral_triggers: list[str] = Field(min_length=1)
    viral_loops: list[str] = Field(min_length=1)
    rationale: str


class PartnershipOpportunityOutput(BaseModel):
    partner_type: str
    expansion_lever: str
    rationale: str
    priority: Literal["high", "medium", "low"]


class PaidAcquisitionPotentialOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    viable_channels: list[str] = Field(min_length=1)
    estimated_cac_range_usd: str
    rationale: str


class MarketExpansionOutput(BaseModel):
    segment_name: str
    geography: str
    expansion_rationale: str
    priority: Literal["high", "medium", "low"]


class GrowthPhaseOutput(BaseModel):
    phase_name: str = Field(max_length=80)
    duration_months: int = Field(ge=1)
    focus: str
    growth_levers: list[str] = Field(min_length=1)
    milestones: list[str] = Field(min_length=1)


class GrowthEvidenceOutput(BaseModel):
    evidence_type: Literal[
        "market_signal",
        "demand_signal",
        "competitive_gap",
        "expansion_signal",
        "channel_signal",
    ]
    excerpt: str
    source_reference: str
    supports_conclusion: Literal[
        "seo",
        "referral",
        "partnership",
        "paid",
        "expansion",
        "growth_score",
    ]
    confidence: Literal["high", "medium", "low"]
    complaint_index: int | None = None


class GrowthStrategyLLMOutput(BaseModel):
    growth_score: int = Field(ge=0, le=100)
    scalability_score: int = Field(ge=0, le=100)
    risk_score: int = Field(ge=0, le=100)
    seo_potential: SEOPotentialOutput
    referral_potential: ReferralPotentialOutput
    partnership_opportunities: list[PartnershipOpportunityOutput] = Field(min_length=1)
    paid_acquisition_potential: PaidAcquisitionPotentialOutput
    market_expansion_opportunities: list[MarketExpansionOutput] = Field(min_length=1)
    growth_phases: list[GrowthPhaseOutput] = Field(min_length=1)
    supporting_evidence: list[GrowthEvidenceOutput] = Field(min_length=1)
    executive_summary: str


class OpportunityGrowthContext(BaseModel):
    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    frequency_signal: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    complaint_evidence: list[ComplaintEvidenceItem] = Field(default_factory=list)


class GrowthStrategyDraft(BaseModel):
    growth_score: int
    scalability_score: int
    risk_score: int
    seo_potential: SEOPotentialOutput
    referral_potential: ReferralPotentialOutput
    partnership_opportunities: list[PartnershipOpportunityOutput]
    paid_acquisition_potential: PaidAcquisitionPotentialOutput
    market_expansion_opportunities: list[MarketExpansionOutput]
    growth_roadmap: list[dict[str, Any]]
    supporting_evidence: list[GrowthEvidenceOutput]
    executive_summary: str
    evaluation_metrics: dict[str, Any]


class GrowthStrategyResult(BaseModel):
    opportunity_id: UUID
    growth_evaluation_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: GrowthStrategyDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class GrowthStrategyBatchResult(BaseModel):
    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[GrowthStrategyResult] = Field(default_factory=list)

    def add(self, item: GrowthStrategyResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: GrowthStrategyLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
