"""Schemas for the go-to-market agent."""

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


class IdealCustomerProfileOutput(BaseModel):
    summary: str
    company_size: str
    industry: str
    geography: str
    budget_range: str
    buying_triggers: list[str] = Field(min_length=1)


class CustomerPersonaOutput(BaseModel):
    persona_name: str = Field(max_length=120)
    role: str
    goals: list[str] = Field(min_length=1)
    pain_points: list[str] = Field(min_length=1)
    preferred_channels: list[str] = Field(min_length=1)


class AcquisitionChannelOutput(BaseModel):
    channel_name: str = Field(max_length=80)
    channel_type: Literal[
        "content",
        "community",
        "partnership",
        "paid",
        "outbound",
        "product_led",
        "events",
    ]
    rationale: str
    priority: Literal["primary", "secondary", "experimental"]
    estimated_cac_usd: float = Field(ge=0)


class OutreachStrategyOutput(BaseModel):
    primary_motion: str
    messaging_themes: list[str] = Field(min_length=1)
    cadence: str
    conversion_tactics: list[str] = Field(min_length=1)


class ContentStrategyOutput(BaseModel):
    themes: list[str] = Field(min_length=1)
    formats: list[str] = Field(min_length=1)
    distribution_plan: str
    publishing_cadence: str


class SEOOpportunityOutput(BaseModel):
    keyword_theme: str
    search_intent: str
    content_angle: str
    priority: Literal["high", "medium", "low"]


class PartnershipOutput(BaseModel):
    partner_type: str
    partner_examples: list[str] = Field(min_length=1)
    value_exchange: str
    priority: Literal["high", "medium", "low"]


class First100CustomersPlanOutput(BaseModel):
    target_segments: list[str] = Field(min_length=1)
    acquisition_tactics: list[str] = Field(min_length=1)
    weekly_targets: list[str] = Field(min_length=1)
    success_metrics: list[str] = Field(min_length=1)


class AcquisitionPhaseOutput(BaseModel):
    phase_name: str = Field(max_length=80)
    duration_weeks: int = Field(ge=1)
    focus: str
    channels: list[str] = Field(min_length=1)
    targets: list[str] = Field(min_length=1)
    milestones: list[str] = Field(min_length=1)


class GTMEvidenceOutput(BaseModel):
    evidence_type: Literal[
        "pain_point",
        "audience_signal",
        "channel_signal",
        "competitor_gap",
        "buyer_behavior",
    ]
    excerpt: str
    source_reference: str
    supports_conclusion: Literal[
        "icp",
        "persona",
        "channel",
        "outreach",
        "content",
        "seo",
        "partnership",
        "first_100",
    ]
    confidence: Literal["high", "medium", "low"]
    complaint_index: int | None = None


class GoToMarketLLMOutput(BaseModel):
    ideal_customer_profile: IdealCustomerProfileOutput
    customer_personas: list[CustomerPersonaOutput] = Field(min_length=1)
    acquisition_channels: list[AcquisitionChannelOutput] = Field(min_length=1)
    outreach_strategy: OutreachStrategyOutput
    content_strategy: ContentStrategyOutput
    seo_opportunities: list[SEOOpportunityOutput] = Field(min_length=1)
    partnerships: list[PartnershipOutput] = Field(min_length=1)
    first_100_customers_plan: First100CustomersPlanOutput
    acquisition_phases: list[AcquisitionPhaseOutput] = Field(min_length=1)
    estimated_cac_usd: float = Field(ge=0)
    confidence_score: int = Field(ge=0, le=100)
    gtm_report: str
    supporting_evidence: list[GTMEvidenceOutput] = Field(min_length=1)


class OpportunityGTMContext(BaseModel):
    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    frequency_signal: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    complaint_evidence: list[ComplaintEvidenceItem] = Field(default_factory=list)


class GoToMarketDraft(BaseModel):
    ideal_customer_profile: IdealCustomerProfileOutput
    customer_personas: list[CustomerPersonaOutput]
    acquisition_channels: list[AcquisitionChannelOutput]
    outreach_strategy: OutreachStrategyOutput
    content_strategy: ContentStrategyOutput
    seo_opportunities: list[SEOOpportunityOutput]
    partnerships: list[PartnershipOutput]
    first_100_customers_plan: First100CustomersPlanOutput
    acquisition_roadmap: list[dict[str, Any]]
    estimated_cac_usd: float
    confidence_score: int
    gtm_report: str
    supporting_evidence: list[GTMEvidenceOutput]
    ranking_metrics: dict[str, Any]


class GoToMarketResult(BaseModel):
    opportunity_id: UUID
    gtm_plan_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: GoToMarketDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class GoToMarketBatchResult(BaseModel):
    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[GoToMarketResult] = Field(default_factory=list)

    def add(self, item: GoToMarketResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: GoToMarketLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
