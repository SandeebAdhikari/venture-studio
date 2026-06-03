"""Executive ranking persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import ExecutiveRankingStatus
from app.db.models.executive_ranking_entry import ExecutiveRankingEntry
from app.db.models.executive_ranking_run import ExecutiveRankingRun


class ExecutiveRankingEntryCreate(BaseModel):
    opportunity_id: UUID
    rank: int = Field(ge=1)
    final_opportunity_score: int = Field(ge=0, le=100)
    pain_score: int | None = Field(default=None, ge=0, le=100)
    market_score: int | None = Field(default=None, ge=0, le=100)
    revenue_score: int | None = Field(default=None, ge=0, le=100)
    competition_score: int | None = Field(default=None, ge=0, le=100)
    growth_score: int | None = Field(default=None, ge=0, le=100)
    founder_fit_score: int | None = Field(default=None, ge=0, le=100)
    agent_coverage_count: int = Field(ge=0)
    is_top_opportunity: bool = False
    source_references: dict[str, Any] = Field(default_factory=dict)
    ranking_details: dict[str, Any] = Field(default_factory=dict)


class ExecutiveRankingRunCreate(BaseModel):
    status: ExecutiveRankingStatus = ExecutiveRankingStatus.COMPLETED
    founder_profile_id: UUID | None = None
    top_n: int = Field(default=5, ge=1)
    opportunity_count: int = Field(default=0, ge=0)
    ranked_opportunity_count: int = Field(default=0, ge=0)
    ranking_engine: str
    ranking_metadata: dict[str, Any] = Field(default_factory=dict)
    entries: list[ExecutiveRankingEntryCreate] = Field(default_factory=list)


class ExecutiveRankingEntryRead(BaseModel):
    id: UUID
    opportunity_id: UUID
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

    @classmethod
    def from_entity(cls, entity: ExecutiveRankingEntry) -> "ExecutiveRankingEntryRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            rank=entity.rank,
            final_opportunity_score=entity.final_opportunity_score,
            pain_score=entity.pain_score,
            market_score=entity.market_score,
            revenue_score=entity.revenue_score,
            competition_score=entity.competition_score,
            growth_score=entity.growth_score,
            founder_fit_score=entity.founder_fit_score,
            agent_coverage_count=entity.agent_coverage_count,
            is_top_opportunity=entity.is_top_opportunity,
            source_references=entity.source_references,
            ranking_details=entity.ranking_details,
        )


class ExecutiveRankingRunRead(BaseModel):
    id: UUID
    version: int
    status: ExecutiveRankingStatus
    is_current: bool
    founder_profile_id: UUID | None
    top_n: int
    opportunity_count: int
    ranked_opportunity_count: int
    ranking_engine: str
    ranking_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: ExecutiveRankingRun) -> "ExecutiveRankingRunRead":
        return cls(
            id=entity.id,
            version=entity.version,
            status=ExecutiveRankingStatus(entity.status),
            is_current=entity.is_current,
            founder_profile_id=entity.founder_profile_id,
            top_n=entity.top_n,
            opportunity_count=entity.opportunity_count,
            ranked_opportunity_count=entity.ranked_opportunity_count,
            ranking_engine=entity.ranking_engine,
            ranking_metadata=entity.ranking_metadata,
        )


class ExecutiveRankingRunDetail(ExecutiveRankingRunRead):
    entries: list[ExecutiveRankingEntryRead] = Field(default_factory=list)
    top_opportunities: list[ExecutiveRankingEntryRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: ExecutiveRankingRun) -> "ExecutiveRankingRunDetail":
        base = ExecutiveRankingRunRead.from_entity(entity)
        entries = [ExecutiveRankingEntryRead.from_entity(item) for item in entity.entries]
        top_opportunities = [entry for entry in entries if entry.is_top_opportunity]
        return cls(
            **base.model_dump(),
            entries=entries,
            top_opportunities=top_opportunities,
        )
