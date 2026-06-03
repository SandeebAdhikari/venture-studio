"""Competitor analysis persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import CompetitorAnalysisStatus, ReviewSentiment
from app.db.models.competitor_analysis import CompetitorAnalysis
from app.db.models.competitor_profile import CompetitorProfile


class CompetitorProfileCreate(BaseModel):
    name: str
    positioning: str
    pricing_model: dict[str, Any]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    customer_complaints: list[dict[str, Any]] = Field(default_factory=list)
    review_sentiment: str
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    source_basis: str | None = None
    profile_metadata: dict[str, Any] = Field(default_factory=dict)


class CompetitorAnalysisCreate(BaseModel):
    opportunity_id: UUID
    status: CompetitorAnalysisStatus = CompetitorAnalysisStatus.COMPLETED
    competitive_gaps: list[dict[str, Any]] = Field(default_factory=list)
    executive_summary: str | None = None
    evaluation_metrics: dict[str, Any] = Field(default_factory=dict)
    llm_model: str
    analysis_metadata: dict[str, Any] = Field(default_factory=dict)
    profiles: list[CompetitorProfileCreate] = Field(default_factory=list)


class CompetitorProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    positioning: str
    pricing_model: dict[str, Any]
    strengths: list[str]
    weaknesses: list[str]
    customer_complaints: list[dict[str, Any]]
    review_sentiment: ReviewSentiment
    sentiment_score: float
    source_basis: str | None
    profile_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: CompetitorProfile) -> "CompetitorProfileRead":
        return cls(
            id=entity.id,
            name=entity.name,
            positioning=entity.positioning,
            pricing_model=entity.pricing_model,
            strengths=entity.strengths,
            weaknesses=entity.weaknesses,
            customer_complaints=entity.customer_complaints,
            review_sentiment=ReviewSentiment(entity.review_sentiment),
            sentiment_score=entity.sentiment_score,
            source_basis=entity.source_basis,
            profile_metadata=entity.profile_metadata,
        )


class CompetitorAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    version: int
    status: CompetitorAnalysisStatus
    is_current: bool
    competitive_gaps: list[dict[str, Any]]
    executive_summary: str | None
    evaluation_metrics: dict[str, Any]
    llm_model: str
    analysis_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: CompetitorAnalysis) -> "CompetitorAnalysisRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            version=entity.version,
            status=CompetitorAnalysisStatus(entity.status),
            is_current=entity.is_current,
            competitive_gaps=entity.competitive_gaps,
            executive_summary=entity.executive_summary,
            evaluation_metrics=entity.evaluation_metrics,
            llm_model=entity.llm_model,
            analysis_metadata=entity.analysis_metadata,
        )


class CompetitorAnalysisDetail(CompetitorAnalysisRead):
    profiles: list[CompetitorProfileRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: CompetitorAnalysis) -> "CompetitorAnalysisDetail":
        base = CompetitorAnalysisRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            profiles=[CompetitorProfileRead.from_entity(profile) for profile in entity.profiles],
        )
