"""Schemas for the customer research agent."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ComplaintEvidenceItem(BaseModel):
    """Complaint evidence indexed for LLM grounding."""

    index: int
    complaint_id: UUID
    signal_id: UUID
    summary: str
    verbatim_quote: str
    severity: int = Field(ge=1, le=5)
    source_type: str
    source_name: str
    url: str


class SupportingEvidenceOutput(BaseModel):
    """Evidence item supporting a customer research conclusion."""

    evidence_type: Literal["complaint", "discussion", "review", "forum", "social"]
    excerpt: str
    source_reference: str
    supports_conclusion: Literal["pain", "urgency", "frequency", "sentiment"]
    confidence: Literal["high", "medium", "low"]
    complaint_index: int | None = Field(
        default=None,
        description="Index into provided complaint evidence when grounded.",
    )


class RepresentativeComplaintOutput(BaseModel):
    """Representative customer complaint selected for the research brief."""

    summary: str
    verbatim_quote: str
    severity: int = Field(ge=1, le=5)
    source_type: Literal["complaint", "discussion", "review", "forum", "social"]
    complaint_index: int | None = None


class CustomerResearchLLMOutput(BaseModel):
    """Structured LLM output for customer demand research."""

    pain_score: int = Field(ge=0, le=100)
    urgency_score: int = Field(ge=0, le=100)
    frequency_score: int = Field(ge=0, le=100)
    customer_sentiment: Literal["positive", "neutral", "negative", "mixed"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    cares_verdict: Literal["yes", "partial", "no"]
    representative_complaints: list[RepresentativeComplaintOutput] = Field(min_length=1)
    supporting_evidence: list[SupportingEvidenceOutput] = Field(min_length=1)
    executive_summary: str


class OpportunityCustomerContext(BaseModel):
    """Opportunity context passed to the customer research agent."""

    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    frequency_signal: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    complaint_evidence: list[ComplaintEvidenceItem] = Field(default_factory=list)


class CustomerResearchDraft(BaseModel):
    """Validated customer research ready for persistence."""

    pain_score: int
    urgency_score: int
    frequency_score: int
    customer_sentiment: Literal["positive", "neutral", "negative", "mixed"]
    sentiment_score: float
    cares_verdict: Literal["yes", "partial", "no"]
    representative_complaints: list[RepresentativeComplaintOutput]
    supporting_evidence: list[SupportingEvidenceOutput]
    executive_summary: str
    validation_metrics: dict[str, Any]


class CustomerResearchResult(BaseModel):
    """Result of researching customer demand for one opportunity."""

    opportunity_id: UUID
    customer_research_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: CustomerResearchDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class CustomerResearchBatchResult(BaseModel):
    """Result of a batch customer research run."""

    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[CustomerResearchResult] = Field(default_factory=list)

    def add(self, item: CustomerResearchResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: CustomerResearchLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
