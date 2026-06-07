"""Schemas for the human proxy agent."""

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


class FounderProfileContext(BaseModel):
    founder_profile_id: UUID
    name: str
    skills: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


class FounderFitAnalysisOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    skill_matches: list[str] = Field(min_length=1)
    skill_gaps: list[str] = Field(default_factory=list)
    rationale: str


class ImplementationFeasibilityOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    build_complexity: Literal["low", "medium", "high"]
    rationale: str
    blockers: list[str] = Field(default_factory=list)


class LearningCurveOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    difficulty: Literal["low", "medium", "high"]
    new_skills_required: list[str] = Field(default_factory=list)
    rationale: str


class ExecutionComplexityOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    complexity_level: Literal["low", "medium", "high"]
    operational_burden: str
    rationale: str


class CapitalRequirementsOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    estimated_monthly_usd: str
    bootstrap_friendly: bool
    rationale: str


class ProxyEvidenceOutput(BaseModel):
    evidence_type: Literal[
        "skill_signal",
        "complexity_signal",
        "market_signal",
        "constraint_signal",
        "execution_signal",
    ]
    excerpt: str
    source_reference: str
    supports_conclusion: Literal[
        "founder_fit",
        "feasibility",
        "learning_curve",
        "execution_complexity",
        "capital",
        "recommendation",
    ]
    confidence: Literal["high", "medium", "low"]
    complaint_index: int | None = None


class HumanProxyLLMOutput(BaseModel):
    founder_fit_score: int = Field(ge=0, le=100)
    feasibility_score: int = Field(ge=0, le=100)
    recommendation: Literal["pursue", "explore", "defer", "pass"]
    founder_fit_analysis: FounderFitAnalysisOutput
    implementation_feasibility: ImplementationFeasibilityOutput
    learning_curve: LearningCurveOutput
    execution_complexity: ExecutionComplexityOutput
    capital_requirements: CapitalRequirementsOutput
    supporting_evidence: list[ProxyEvidenceOutput] = Field(min_length=1)
    executive_summary: str


class OpportunityProxyContext(BaseModel):
    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    frequency_signal: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    founder_profile: FounderProfileContext
    complaint_evidence: list[ComplaintEvidenceItem] = Field(default_factory=list)


class HumanProxyDraft(BaseModel):
    founder_fit_score: int
    feasibility_score: int
    recommendation: str
    founder_fit_analysis: FounderFitAnalysisOutput
    implementation_feasibility: ImplementationFeasibilityOutput
    learning_curve: LearningCurveOutput
    execution_complexity: ExecutionComplexityOutput
    capital_requirements: CapitalRequirementsOutput
    supporting_evidence: list[ProxyEvidenceOutput]
    executive_summary: str
    evaluation_metrics: dict[str, Any]
    scale_metadata: dict[str, Any] = Field(default_factory=dict)


class HumanProxyResult(BaseModel):
    opportunity_id: UUID
    founder_profile_id: UUID
    human_proxy_evaluation_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: HumanProxyDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class HumanProxyBatchResult(BaseModel):
    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[HumanProxyResult] = Field(default_factory=list)

    def add(self, item: HumanProxyResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class HumanProxyReevalResult(HumanProxyBatchResult):
    """Batch outcome for HP-REEVAL-1 scale migration re-runs."""

    profiles_processed: int = 0
    targets_identified: int = 0
    skipped_century_v1: int = 0
    dry_run: bool = False


class LLMInvocationResult(BaseModel):
    parsed: HumanProxyLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
