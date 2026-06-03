"""Growth evaluation persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import GrowthEvaluationStatus
from app.db.models.growth_evaluation import GrowthEvaluation
from app.db.models.growth_evaluation_evidence import GrowthEvaluationEvidence


class GrowthEvaluationEvidenceCreate(BaseModel):
    evidence_type: str
    excerpt: str
    source_reference: str
    url: str | None = None
    supports_conclusion: str
    confidence: str
    complaint_id: UUID | None = None
    signal_id: UUID | None = None


class GrowthEvaluationCreate(BaseModel):
    opportunity_id: UUID
    status: GrowthEvaluationStatus = GrowthEvaluationStatus.COMPLETED
    growth_score: int = Field(ge=0, le=100)
    scalability_score: int = Field(ge=0, le=100)
    risk_score: int = Field(ge=0, le=100)
    seo_potential: dict[str, Any] = Field(default_factory=dict)
    referral_potential: dict[str, Any] = Field(default_factory=dict)
    partnership_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    paid_acquisition_potential: dict[str, Any] = Field(default_factory=dict)
    market_expansion_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    growth_roadmap: list[dict[str, Any]] = Field(default_factory=list)
    executive_summary: str | None = None
    evaluation_metrics: dict[str, Any] = Field(default_factory=dict)
    llm_model: str
    evaluation_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[GrowthEvaluationEvidenceCreate] = Field(default_factory=list)


class GrowthEvaluationEvidenceRead(BaseModel):
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

    @classmethod
    def from_entity(cls, entity: GrowthEvaluationEvidence) -> "GrowthEvaluationEvidenceRead":
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
        )


class GrowthEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    version: int
    status: GrowthEvaluationStatus
    is_current: bool
    growth_score: int
    scalability_score: int
    risk_score: int
    seo_potential: dict[str, Any]
    referral_potential: dict[str, Any]
    partnership_opportunities: list[dict[str, Any]]
    paid_acquisition_potential: dict[str, Any]
    market_expansion_opportunities: list[dict[str, Any]]
    growth_roadmap: list[dict[str, Any]]
    executive_summary: str | None
    evaluation_metrics: dict[str, Any]
    llm_model: str
    evaluation_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: GrowthEvaluation) -> "GrowthEvaluationRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            version=entity.version,
            status=GrowthEvaluationStatus(entity.status),
            is_current=entity.is_current,
            growth_score=entity.growth_score,
            scalability_score=entity.scalability_score,
            risk_score=entity.risk_score,
            seo_potential=entity.seo_potential,
            referral_potential=entity.referral_potential,
            partnership_opportunities=entity.partnership_opportunities,
            paid_acquisition_potential=entity.paid_acquisition_potential,
            market_expansion_opportunities=entity.market_expansion_opportunities,
            growth_roadmap=entity.growth_roadmap,
            executive_summary=entity.executive_summary,
            evaluation_metrics=entity.evaluation_metrics,
            llm_model=entity.llm_model,
            evaluation_metadata=entity.evaluation_metadata,
        )


class GrowthEvaluationDetail(GrowthEvaluationRead):
    evidence: list[GrowthEvaluationEvidenceRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: GrowthEvaluation) -> "GrowthEvaluationDetail":
        base = GrowthEvaluationRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            evidence=[GrowthEvaluationEvidenceRead.from_entity(item) for item in entity.evidence],
        )
