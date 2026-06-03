"""Schemas for the opportunity generator agent."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ComplaintEvidence(BaseModel):
    """Complaint data used for pattern detection and synthesis."""

    id: UUID
    summary: str
    verbatim_quote: str
    severity: int = Field(ge=1, le=5)
    domain_code: str
    category_code: str
    persona_code: str
    product_mentions: list[str] = Field(default_factory=list)


class ComplaintPattern(BaseModel):
    """Recurring topic identified across multiple complaints."""

    topic: str
    complaint_ids: list[UUID]
    domain_code: str
    category_code: str
    dominant_persona_code: str
    complaint_count: int
    avg_severity: float


class OpportunityLLMOutput(BaseModel):
    """Structured LLM output for a single opportunity brief."""

    title: str = Field(max_length=200)
    problem_statement: str = Field(description="2-3 sentence explanation of the opportunity.")
    target_user: str
    frequency_signal: str = Field(description="Why this looks recurring based on evidence.")
    existing_alternatives: str = Field(
        description="Products or workarounds mentioned in complaints only.",
    )
    gap: str = Field(description="What is missing in current solutions.")
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(description="Plain-language rationale for the opportunity.")


class OpportunityDraft(BaseModel):
    """Validated opportunity ready for persistence."""

    title: str
    problem_statement: str
    target_user: str
    frequency_signal: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    complaint_ids: list[UUID]
    topic: str


class OpportunityGenerationResult(BaseModel):
    """Result of generating one opportunity from a pattern."""

    pattern_topic: str
    opportunity_id: UUID | None = None
    status: Literal["created", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: OpportunityDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class GenerationBatchResult(BaseModel):
    """Result of a batch opportunity generation run."""

    patterns_found: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[OpportunityGenerationResult] = Field(default_factory=list)

    def add(self, item: OpportunityGenerationResult) -> None:
        self.items.append(item)
        if item.status == "created":
            self.created += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: OpportunityLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
