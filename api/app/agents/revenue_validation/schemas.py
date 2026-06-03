"""Schemas for the revenue validation agent."""

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


class CompetitorPricingContext(BaseModel):
    index: int
    competitor_profile_id: UUID
    name: str
    pricing_model: dict[str, Any]
    positioning: str


class PricingRecommendationOutput(BaseModel):
    tier_name: str = Field(max_length=80)
    price_usd: float = Field(ge=0)
    billing_period: Literal[
        "per_user_monthly",
        "flat_monthly",
        "annual",
        "per_location_monthly",
        "usage_based",
    ]
    target_buyer: str
    rationale: str


class BuyerProfileOutput(BaseModel):
    profile_name: str = Field(max_length=120)
    budget_availability: Literal["high", "medium", "low", "unknown"]
    purchasing_frequency: str
    existing_spending_notes: str


class RevenueEvidenceOutput(BaseModel):
    evidence_type: Literal[
        "existing_spending",
        "competitor_pricing",
        "budget_signal",
        "buyer_profile",
        "purchase_frequency",
    ]
    excerpt: str
    source_reference: str
    supports_conclusion: Literal[
        "willingness_to_pay",
        "pricing",
        "revenue_confidence",
        "budget",
        "frequency",
    ]
    confidence: Literal["high", "medium", "low"]
    complaint_index: int | None = None
    competitor_index: int | None = None


class RevenueValidationLLMOutput(BaseModel):
    willingness_to_pay_score: int = Field(ge=0, le=100)
    revenue_confidence_score: int = Field(ge=0, le=100)
    pricing_recommendations: list[PricingRecommendationOutput] = Field(min_length=1)
    buyer_profiles: list[BuyerProfileOutput] = Field(min_length=1)
    supporting_evidence: list[RevenueEvidenceOutput] = Field(min_length=1)
    executive_summary: str


class OpportunityRevenueContext(BaseModel):
    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    complaint_evidence: list[ComplaintEvidenceItem] = Field(default_factory=list)
    competitor_pricing: list[CompetitorPricingContext] = Field(default_factory=list)


class RevenueValidationDraft(BaseModel):
    willingness_to_pay_score: int
    revenue_confidence_score: int
    pricing_recommendations: list[PricingRecommendationOutput]
    buyer_profiles: list[BuyerProfileOutput]
    supporting_evidence: list[RevenueEvidenceOutput]
    executive_summary: str
    evaluation_metrics: dict[str, Any]


class RevenueValidationResult(BaseModel):
    opportunity_id: UUID
    revenue_validation_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: RevenueValidationDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class RevenueValidationBatchResult(BaseModel):
    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[RevenueValidationResult] = Field(default_factory=list)

    def add(self, item: RevenueValidationResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: RevenueValidationLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
