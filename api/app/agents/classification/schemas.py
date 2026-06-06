"""Schemas for the complaint classification agent."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RawComplaintText(BaseModel):
    """Raw complaint text passed to the classification agent."""

    body: str = Field(min_length=1)
    title: str | None = None
    url: str | None = None
    signal_id: UUID | None = None


class ClassificationLLMOutput(BaseModel):
    """Structured output schema enforced on the LLM response."""

    is_complaint: bool = Field(
        description="True when the text expresses a user pain point or unmet need.",
    )
    industry: str = Field(description="Industry/domain code from the allowed taxonomy.")
    customer_type: str = Field(description="Customer persona code from the allowed taxonomy.")
    problem_category: str = Field(
        description=(
            "Complaint theme code from the allowed taxonomy ONLY "
            "(pricing, security, missing_feature, workflow, …). "
            "Never use billing or billing_operations here — those are not valid problem_category codes."
        ),
    )
    severity_score: int = Field(ge=1, le=5, description="Severity from 1 (mild) to 5 (blocker).")
    summary: str = Field(description="Neutral 1-2 sentence summary of the complaint.")
    verbatim_quote: str = Field(
        description="Exact quote from the source text supporting the complaint.",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the classification.")
    product_mentions: list[str] = Field(default_factory=list)
    business_function_code: str = Field(
        description=(
            "Founder signal: business function code (e.g. payment_processor, billing_operations). "
            "Not a problem_category."
        ),
    )
    jtbd_code: str = Field(
        description="Founder signal: job-to-be-done code (e.g. accept_payments). Not a problem_category.",
    )
    consequence_code: str = Field(
        description=(
            "Founder signal: economic consequence code (e.g. revenue_interruption). "
            "Not a problem_category."
        ),
    )


class ClassificationResult(BaseModel):
    """Public classification output returned by the agent."""

    industry: str
    customer_type: str
    problem_category: str
    severity_score: int = Field(ge=1, le=5)
    summary: str
    is_complaint: bool = True
    verbatim_quote: str | None = None
    confidence: float | None = None
    product_mentions: list[str] = Field(default_factory=list)
    business_function_code: str | None = None
    jtbd_code: str | None = None
    consequence_code: str | None = None


class ClassificationAgentResult(BaseModel):
    """Full agent execution result including persistence metadata."""

    signal_id: UUID | None = None
    complaint_id: UUID | None = None
    status: Literal["classified", "skipped", "failed"]
    classification: ClassificationResult | None = None
    skip_reason: str | None = None
    error: str | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class ClassificationBatchResult(BaseModel):
    classified: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[ClassificationAgentResult] = Field(default_factory=list)

    def add(self, item: ClassificationAgentResult) -> None:
        self.items.append(item)
        if item.status == "classified":
            self.classified += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: ClassificationLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
