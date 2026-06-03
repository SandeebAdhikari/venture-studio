"""Schemas for the product strategy agent."""

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


class CoreFeatureOutput(BaseModel):
    name: str = Field(max_length=120)
    description: str
    user_value: str


class FeaturePriorityOutput(BaseModel):
    feature_name: str = Field(max_length=120)
    priority: Literal["P0", "P1", "P2"]
    rank: int = Field(ge=1)
    rationale: str


class DevelopmentPhaseOutput(BaseModel):
    phase_name: str = Field(max_length=80)
    duration_weeks: int = Field(ge=1)
    deliverables: list[str] = Field(min_length=1)
    milestones: list[str] = Field(min_length=1)


class EstimatedTimelineOutput(BaseModel):
    total_weeks: int = Field(ge=1)
    mvp_weeks: int = Field(ge=1)
    summary: str


class TechnicalRiskOutput(BaseModel):
    risk: str
    severity: Literal["high", "medium", "low"]
    mitigation: str


class StrategyEvidenceOutput(BaseModel):
    evidence_type: Literal["pain_point", "gap", "user_need", "technical_constraint"]
    excerpt: str
    source_reference: str
    supports_conclusion: Literal["mvp", "feature", "phase", "risk", "timeline"]
    confidence: Literal["high", "medium", "low"]
    complaint_index: int | None = None


class ProductStrategyLLMOutput(BaseModel):
    mvp_definition: str
    core_features: list[CoreFeatureOutput] = Field(min_length=1)
    feature_priorities: list[FeaturePriorityOutput] = Field(min_length=1)
    development_phases: list[DevelopmentPhaseOutput] = Field(min_length=1)
    estimated_timeline: EstimatedTimelineOutput
    technical_risks: list[TechnicalRiskOutput] = Field(min_length=1)
    supporting_evidence: list[StrategyEvidenceOutput] = Field(min_length=1)
    executive_summary: str


class OpportunityPlanningContext(BaseModel):
    opportunity_id: UUID
    title: str
    problem_statement: str
    target_user: str
    frequency_signal: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    complaint_evidence: list[ComplaintEvidenceItem] = Field(default_factory=list)


class ProductStrategyDraft(BaseModel):
    mvp_definition: str
    core_features: list[CoreFeatureOutput]
    feature_priorities: list[FeaturePriorityOutput]
    development_phases: list[DevelopmentPhaseOutput]
    estimated_timeline: EstimatedTimelineOutput
    technical_risks: list[TechnicalRiskOutput]
    roadmap: list[dict[str, Any]]
    supporting_evidence: list[StrategyEvidenceOutput]
    executive_summary: str
    planning_metrics: dict[str, Any]


class ProductStrategyResult(BaseModel):
    opportunity_id: UUID
    product_strategy_id: UUID | None = None
    status: Literal["completed", "skipped", "failed"]
    skip_reason: str | None = None
    error: str | None = None
    draft: ProductStrategyDraft | None = None
    attempts: int = 0
    eval_logs: list[dict[str, Any]] = Field(default_factory=list)


class ProductStrategyBatchResult(BaseModel):
    opportunities_found: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[ProductStrategyResult] = Field(default_factory=list)

    def add(self, item: ProductStrategyResult) -> None:
        self.items.append(item)
        if item.status == "completed":
            self.completed += 1
        elif item.status == "skipped":
            self.skipped += 1
        elif item.status == "failed":
            self.failed += 1


class LLMInvocationResult(BaseModel):
    parsed: ProductStrategyLLMOutput | None = None
    raw_text: str | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
