"""Schemas for executive ranking engine."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentSourceReferences(BaseModel):
    market_brief_id: UUID | None = None
    competitor_analysis_id: UUID | None = None
    customer_research_id: UUID | None = None
    revenue_validation_id: UUID | None = None
    product_strategy_id: UUID | None = None
    gtm_plan_id: UUID | None = None
    growth_evaluation_id: UUID | None = None
    human_proxy_evaluation_id: UUID | None = None


class AgentEvaluationInput(BaseModel):
    """Normalized agent outputs used to compute executive ranking scores."""

    opportunity_id: UUID
    opportunity_title: str
    sources: AgentSourceReferences = Field(default_factory=AgentSourceReferences)

    pain_score: int | None = None
    market_score: int | None = None
    revenue_score: int | None = None
    competition_score: int | None = None
    growth_score: int | None = None
    founder_fit_score: int | None = None

    agent_coverage_count: int = 0
    ranking_details: dict[str, Any] = Field(default_factory=dict)


class ExecutiveComponentScores(BaseModel):
    pain_score: int | None = None
    market_score: int | None = None
    revenue_score: int | None = None
    competition_score: int | None = None
    growth_score: int | None = None
    founder_fit_score: int | None = None


class ExecutiveRankingScore(BaseModel):
    opportunity_id: UUID
    opportunity_title: str
    final_opportunity_score: int = Field(ge=0, le=100)
    components: ExecutiveComponentScores
    agent_coverage_count: int
    source_references: AgentSourceReferences
    ranking_details: dict[str, Any] = Field(default_factory=dict)


class ExecutiveRankingEntryRead(BaseModel):
    id: UUID
    opportunity_id: UUID
    opportunity_title: str
    rank: int
    final_opportunity_score: int
    pain_score: int | None
    market_score: int | None
    revenue_score: int | None
    competition_score: int | None
    growth_score: int | None
    founder_fit_score: int | None
    agent_coverage_count: int
    is_top_opportunity: bool
    source_references: dict[str, Any]
    ranking_details: dict[str, Any]


class ExecutiveRankingRunRead(BaseModel):
    id: UUID
    version: int
    status: str
    is_current: bool
    founder_profile_id: UUID | None
    top_n: int
    opportunity_count: int
    ranked_opportunity_count: int
    ranking_engine: str
    ranking_metadata: dict[str, Any]


class ExecutiveRankingResult(BaseModel):
    ranking_run_id: UUID
    version: int
    top_n: int
    ranked_opportunity_count: int
    top_opportunities: list[ExecutiveRankingEntryRead]


class ExecutiveRankingRegenResult(BaseModel):
    """Outcome for EXEC-RANK-REGEN-1 post-HP re-evaluation ranking refresh."""

    dry_run: bool = False
    founder_profile_id: UUID | None = None
    top_n: int = 0
    opportunity_count: int = 0
    rankable_opportunity_count: int = 0
    century_v1_hp_count: int = 0
    stale_entry_count: int = 0
    superseded_run_id: UUID | None = None
    superseded_version: int | None = None
    ranking_run_id: UUID | None = None
    version: int | None = None
    ranked_opportunity_count: int = 0
    top_opportunities: list[ExecutiveRankingEntryRead] = Field(default_factory=list)
