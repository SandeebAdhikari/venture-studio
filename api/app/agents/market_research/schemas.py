"""Schemas for the market research agent."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerSegment(BaseModel):
    """Target customer segment within the serviceable market."""

    name: str = Field(max_length=120)
    description: str
    estimated_share_pct: float | None = Field(default=None, ge=0.0, le=100.0)


class IndustryTrend(BaseModel):
    """Industry trend relevant to the opportunity."""

    trend: str = Field(max_length=200)
    description: str
    relevance: str = Field(description="Why this trend matters for the opportunity.")


class SupportingEvidence(BaseModel):
    """Evidence backing a market intelligence claim."""

    claim: str
    source_type: Literal[
        "industry_report",
        "public_market_data",
        "demographic_data",
        "technology_trend",
        "inference_from_complaints",
    ]
    source_reference: str = Field(
        description="Named source, dataset, or reasoning basis for the claim.",
    )
    confidence: Literal["high", "medium", "low"]


class MarketResearchLLMOutput(BaseModel):
    """Structured LLM output for market intelligence on an opportunity."""

    market_size_usd: float = Field(
        ge=0,
        description="Total relevant industry/market size in USD.",
    )
    tam_usd: float = Field(ge=0, description="Total addressable market in USD.")
    sam_usd: float = Field(ge=0, description="Serviceable addressable market in USD.")
    industry_growth_rate_pct: float = Field(
        ge=-50.0,
        le=100.0,
        description="Estimated annual industry growth rate as a percentage.",
    )
    customer_segments: list[CustomerSegment] = Field(min_length=1)
    industry_trends: list[IndustryTrend] = Field(min_length=1)
    supporting_evidence: list[SupportingEvidence] = Field(min_length=1)
    executive_summary: str = Field(
        description="2-4 sentence summary of market intelligence findings.",
    )


class OpportunityResearchContext(BaseModel):
    """Opportunity context passed to the market research agent."""

    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    frequency_signal: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    domain_codes: list[str] = Field(default_factory=list)
    category_codes: list[str] = Field(default_factory=list)
    persona_codes: list[str] = Field(default_factory=list)
    complaint_summaries: list[str] = Field(default_factory=list)


class MarketResearchDraft(BaseModel):
    """Validated market intelligence ready for persistence."""

    market_size_usd: float
    tam_usd: float
    sam_usd: float
    industry_growth_rate_pct: float
    customer_segments: list[CustomerSegment]
    industry_trends: list[IndustryTrend]
    supporting_evidence: list[SupportingEvidence]
    executive_summary: str


class MarketResearchResult(BaseModel):
    """Result of researching one opportunity."""

    opportunity_id: UUID
    market_brief_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: MarketResearchDraft | None = None
    attempts: int = 0
    validation_errors: list[str] = Field(default_factory=list)
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class MarketResearchBatchResult(BaseModel):
    """Result of a batch market research run."""

    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[MarketResearchResult] = Field(default_factory=list)

    def add(self, item: MarketResearchResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: MarketResearchLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
