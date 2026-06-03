"""Schemas for the opportunity scoring engine."""

from uuid import UUID

from pydantic import BaseModel, Field


class ScoringInput(BaseModel):
    """Evidence gathered from an opportunity and linked complaints."""

    opportunity_id: UUID
    confidence_score: float = Field(ge=0.0, le=1.0)
    complaint_count: int = Field(ge=0)
    avg_severity: float = Field(ge=0.0, le=5.0)
    max_severity: int = Field(ge=1, le=5)
    domain_code: str
    category_code: str
    dominant_persona_code: str
    unique_product_count: int = Field(ge=0)
    has_documented_alternatives: bool = False
    gap_text: str = ""


class DimensionScores(BaseModel):
    volume: int = Field(ge=0, le=100)
    severity: int = Field(ge=0, le=100)
    market_indicators: int = Field(ge=0, le=100)
    implementation_ease: int = Field(ge=0, le=100)
    founder_fit: int = Field(ge=0, le=100)


class ScoringResult(BaseModel):
    score: int = Field(ge=0, le=100)
    dimensions: DimensionScores
    volume_score: float = Field(ge=0.0, le=1.0)
    severity_score: float = Field(ge=0.0, le=1.0)
    market_indicator_score: float = Field(ge=0.0, le=1.0)
    implementation_ease_score: float = Field(ge=0.0, le=1.0)
    founder_fit_score: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str


class OpportunityScoreRecord(BaseModel):
    """Persisted score row returned by the scoring service."""

    id: UUID
    opportunity_id: UUID
    score: int
    is_current: bool
    scoring_model: str
    explanation: str | None = None
    dimensions: DimensionScores
