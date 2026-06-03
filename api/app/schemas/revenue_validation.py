"""Revenue validation persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import RevenueValidationStatus
from app.db.models.revenue_validation import RevenueValidation
from app.db.models.revenue_validation_evidence import RevenueValidationEvidence


class RevenueValidationEvidenceCreate(BaseModel):
    evidence_type: str
    excerpt: str
    source_reference: str
    url: str | None = None
    supports_conclusion: str
    confidence: str
    complaint_id: UUID | None = None
    signal_id: UUID | None = None
    competitor_profile_id: UUID | None = None


class RevenueValidationCreate(BaseModel):
    opportunity_id: UUID
    status: RevenueValidationStatus = RevenueValidationStatus.COMPLETED
    willingness_to_pay_score: int = Field(ge=0, le=100)
    revenue_confidence_score: int = Field(ge=0, le=100)
    pricing_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    buyer_profiles: list[dict[str, Any]] = Field(default_factory=list)
    executive_summary: str | None = None
    evaluation_metrics: dict[str, Any] = Field(default_factory=dict)
    llm_model: str
    validation_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[RevenueValidationEvidenceCreate] = Field(default_factory=list)


class RevenueValidationEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evidence_type: str
    excerpt: str
    source_reference: str
    url: str | None
    supports_conclusion: str
    confidence: str
    complaint_id: UUID | None
    signal_id: UUID | None
    competitor_profile_id: UUID | None

    @classmethod
    def from_entity(cls, entity: RevenueValidationEvidence) -> "RevenueValidationEvidenceRead":
        return cls(
            id=entity.id,
            evidence_type=entity.evidence_type,
            excerpt=entity.excerpt,
            source_reference=entity.source_reference,
            url=entity.url,
            supports_conclusion=entity.supports_conclusion,
            confidence=entity.confidence,
            complaint_id=entity.complaint_id,
            signal_id=entity.signal_id,
            competitor_profile_id=entity.competitor_profile_id,
        )


class RevenueValidationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    version: int
    status: RevenueValidationStatus
    is_current: bool
    willingness_to_pay_score: int
    revenue_confidence_score: int
    pricing_recommendations: list[dict[str, Any]]
    buyer_profiles: list[dict[str, Any]]
    executive_summary: str | None
    evaluation_metrics: dict[str, Any]
    llm_model: str
    validation_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: RevenueValidation) -> "RevenueValidationRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            version=entity.version,
            status=RevenueValidationStatus(entity.status),
            is_current=entity.is_current,
            willingness_to_pay_score=entity.willingness_to_pay_score,
            revenue_confidence_score=entity.revenue_confidence_score,
            pricing_recommendations=entity.pricing_recommendations,
            buyer_profiles=entity.buyer_profiles,
            executive_summary=entity.executive_summary,
            evaluation_metrics=entity.evaluation_metrics,
            llm_model=entity.llm_model,
            validation_metadata=entity.validation_metadata,
        )


class RevenueValidationDetail(RevenueValidationRead):
    evidence: list[RevenueValidationEvidenceRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: RevenueValidation) -> "RevenueValidationDetail":
        base = RevenueValidationRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            evidence=[RevenueValidationEvidenceRead.from_entity(item) for item in entity.evidence],
        )
