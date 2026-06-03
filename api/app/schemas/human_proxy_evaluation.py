"""Human proxy evaluation persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import FounderRecommendation, HumanProxyEvaluationStatus
from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
from app.db.models.human_proxy_evaluation_evidence import HumanProxyEvaluationEvidence


class HumanProxyEvaluationEvidenceCreate(BaseModel):
    evidence_type: str
    excerpt: str
    source_reference: str
    url: str | None = None
    supports_conclusion: str
    confidence: str
    complaint_id: UUID | None = None
    signal_id: UUID | None = None


class HumanProxyEvaluationCreate(BaseModel):
    opportunity_id: UUID
    founder_profile_id: UUID
    status: HumanProxyEvaluationStatus = HumanProxyEvaluationStatus.COMPLETED
    founder_fit_score: int = Field(ge=0, le=100)
    feasibility_score: int = Field(ge=0, le=100)
    recommendation: str
    founder_fit_analysis: dict[str, Any] = Field(default_factory=dict)
    implementation_feasibility: dict[str, Any] = Field(default_factory=dict)
    learning_curve: dict[str, Any] = Field(default_factory=dict)
    execution_complexity: dict[str, Any] = Field(default_factory=dict)
    capital_requirements: dict[str, Any] = Field(default_factory=dict)
    executive_summary: str | None = None
    evaluation_metrics: dict[str, Any] = Field(default_factory=dict)
    llm_model: str
    proxy_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[HumanProxyEvaluationEvidenceCreate] = Field(default_factory=list)


class HumanProxyEvaluationEvidenceRead(BaseModel):
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
    def from_entity(cls, entity: HumanProxyEvaluationEvidence) -> "HumanProxyEvaluationEvidenceRead":
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


class HumanProxyEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    founder_profile_id: UUID
    version: int
    status: HumanProxyEvaluationStatus
    is_current: bool
    founder_fit_score: int
    feasibility_score: int
    recommendation: FounderRecommendation
    founder_fit_analysis: dict[str, Any]
    implementation_feasibility: dict[str, Any]
    learning_curve: dict[str, Any]
    execution_complexity: dict[str, Any]
    capital_requirements: dict[str, Any]
    executive_summary: str | None
    evaluation_metrics: dict[str, Any]
    llm_model: str
    proxy_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: HumanProxyEvaluation) -> "HumanProxyEvaluationRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            founder_profile_id=entity.founder_profile_id,
            version=entity.version,
            status=HumanProxyEvaluationStatus(entity.status),
            is_current=entity.is_current,
            founder_fit_score=entity.founder_fit_score,
            feasibility_score=entity.feasibility_score,
            recommendation=FounderRecommendation(entity.recommendation),
            founder_fit_analysis=entity.founder_fit_analysis,
            implementation_feasibility=entity.implementation_feasibility,
            learning_curve=entity.learning_curve,
            execution_complexity=entity.execution_complexity,
            capital_requirements=entity.capital_requirements,
            executive_summary=entity.executive_summary,
            evaluation_metrics=entity.evaluation_metrics,
            llm_model=entity.llm_model,
            proxy_metadata=entity.proxy_metadata,
        )


class HumanProxyEvaluationDetail(HumanProxyEvaluationRead):
    evidence: list[HumanProxyEvaluationEvidenceRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: HumanProxyEvaluation) -> "HumanProxyEvaluationDetail":
        base = HumanProxyEvaluationRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            evidence=[
                HumanProxyEvaluationEvidenceRead.from_entity(item) for item in entity.evidence
            ],
        )
