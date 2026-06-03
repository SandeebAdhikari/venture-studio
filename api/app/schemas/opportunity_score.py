"""Pydantic schemas for opportunity scores."""

from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, UUIDSchema


class OpportunityScoreBase(ORMModel):
    score: int = Field(ge=0, le=100)
    overall_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    frequency_score: float = Field(ge=0.0, le=1.0)
    severity_score: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    volume_score: float = Field(ge=0.0, le=1.0)
    market_indicator_score: float = Field(ge=0.0, le=1.0)
    implementation_ease_score: float = Field(ge=0.0, le=1.0)
    founder_fit_score: float = Field(ge=0.0, le=1.0)
    scoring_model: str = Field(max_length=50)
    scoring_notes: str | None = None
    is_current: bool = True


class OpportunityScoreCreate(OpportunityScoreBase):
    opportunity_id: UUID


class OpportunityScoreUpdate(ORMModel):
    score: int | None = Field(default=None, ge=0, le=100)
    overall_score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    frequency_score: float | None = Field(default=None, ge=0.0, le=1.0)
    severity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    volume_score: float | None = Field(default=None, ge=0.0, le=1.0)
    market_indicator_score: float | None = Field(default=None, ge=0.0, le=1.0)
    implementation_ease_score: float | None = Field(default=None, ge=0.0, le=1.0)
    founder_fit_score: float | None = Field(default=None, ge=0.0, le=1.0)
    scoring_model: str | None = Field(default=None, max_length=50)
    scoring_notes: str | None = None
    is_current: bool | None = None


class OpportunityScoreRead(OpportunityScoreBase, UUIDSchema):
    opportunity_id: UUID
