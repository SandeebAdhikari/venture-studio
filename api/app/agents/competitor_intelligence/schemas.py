"""Schemas for the competitor intelligence agent."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CompetitorPricingModel(BaseModel):
    """Pricing structure for a competitor."""

    model_type: Literal[
        "subscription",
        "freemium",
        "usage_based",
        "one_time",
        "enterprise",
        "unknown",
    ]
    starting_price_usd: float | None = Field(default=None, ge=0)
    billing_period: str | None = Field(
        default=None,
        description="e.g. per_user_monthly, flat_monthly, annual",
    )
    pricing_notes: str


class CustomerComplaintSummary(BaseModel):
    """Summarized customer complaint theme for a competitor."""

    summary: str
    theme: str
    sentiment: Literal["negative", "mixed", "neutral"]


class CompetitorProfileOutput(BaseModel):
    """Structured competitor profile from LLM analysis."""

    name: str = Field(max_length=120)
    positioning: str
    pricing: CompetitorPricingModel
    strengths: list[str] = Field(min_length=1)
    weaknesses: list[str] = Field(min_length=1)
    customer_complaints: list[CustomerComplaintSummary] = Field(min_length=1)
    review_sentiment: Literal["positive", "neutral", "negative", "mixed"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    source_basis: str = Field(
        description="How this competitor was identified (evidence, category knowledge, etc.).",
    )


class CompetitiveGap(BaseModel):
    """Gap in the competitive landscape the opportunity could exploit."""

    gap: str = Field(max_length=200)
    description: str
    opportunity_angle: str
    affected_competitors: list[str] = Field(default_factory=list)


class CompetitorAnalysisLLMOutput(BaseModel):
    """Structured LLM output for competitor intelligence."""

    competitors: list[CompetitorProfileOutput] = Field(min_length=1)
    competitive_gaps: list[CompetitiveGap] = Field(min_length=1)
    executive_summary: str = Field(
        description="2-4 sentence summary of the competitive landscape.",
    )


class OpportunityCompetitorContext(BaseModel):
    """Opportunity context passed to the competitor intelligence agent."""

    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    known_products: list[str] = Field(default_factory=list)
    complaint_summaries: list[str] = Field(default_factory=list)
    product_mentions: list[str] = Field(default_factory=list)


class CompetitorProfileDraft(BaseModel):
    name: str
    positioning: str
    pricing: CompetitorPricingModel
    strengths: list[str]
    weaknesses: list[str]
    customer_complaints: list[CustomerComplaintSummary]
    review_sentiment: Literal["positive", "neutral", "negative", "mixed"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    source_basis: str


class CompetitorAnalysisDraft(BaseModel):
    """Validated competitor analysis ready for persistence."""

    competitors: list[CompetitorProfileDraft]
    competitive_gaps: list[CompetitiveGap]
    executive_summary: str
    evaluation_metrics: dict[str, Any]


class CompetitorAnalysisResult(BaseModel):
    """Result of analyzing competitors for one opportunity."""

    opportunity_id: UUID
    competitor_analysis_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: CompetitorAnalysisDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class CompetitorAnalysisBatchResult(BaseModel):
    """Result of a batch competitor analysis run."""

    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[CompetitorAnalysisResult] = Field(default_factory=list)

    def add(self, item: CompetitorAnalysisResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: CompetitorAnalysisLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
