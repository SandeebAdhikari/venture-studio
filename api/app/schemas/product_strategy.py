"""Product strategy persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ProductStrategyStatus
from app.db.models.product_strategy import ProductStrategy
from app.db.models.product_strategy_evidence import ProductStrategyEvidence


class ProductStrategyEvidenceCreate(BaseModel):
    evidence_type: str
    excerpt: str
    source_reference: str
    url: str | None = None
    supports_conclusion: str
    confidence: str
    complaint_id: UUID | None = None
    signal_id: UUID | None = None


class ProductStrategyCreate(BaseModel):
    opportunity_id: UUID
    status: ProductStrategyStatus = ProductStrategyStatus.COMPLETED
    mvp_definition: str
    core_features: list[dict[str, Any]] = Field(default_factory=list)
    feature_priorities: list[dict[str, Any]] = Field(default_factory=list)
    development_phases: list[dict[str, Any]] = Field(default_factory=list)
    estimated_timeline: dict[str, Any] = Field(default_factory=dict)
    technical_risks: list[dict[str, Any]] = Field(default_factory=list)
    roadmap: list[dict[str, Any]] = Field(default_factory=list)
    executive_summary: str | None = None
    planning_metrics: dict[str, Any] = Field(default_factory=dict)
    llm_model: str
    strategy_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[ProductStrategyEvidenceCreate] = Field(default_factory=list)


class ProductStrategyEvidenceRead(BaseModel):
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
    def from_entity(cls, entity: ProductStrategyEvidence) -> "ProductStrategyEvidenceRead":
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


class ProductStrategyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    version: int
    status: ProductStrategyStatus
    is_current: bool
    mvp_definition: str
    core_features: list[dict[str, Any]]
    feature_priorities: list[dict[str, Any]]
    development_phases: list[dict[str, Any]]
    estimated_timeline: dict[str, Any]
    technical_risks: list[dict[str, Any]]
    roadmap: list[dict[str, Any]]
    executive_summary: str | None
    planning_metrics: dict[str, Any]
    llm_model: str
    strategy_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: ProductStrategy) -> "ProductStrategyRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            version=entity.version,
            status=ProductStrategyStatus(entity.status),
            is_current=entity.is_current,
            mvp_definition=entity.mvp_definition,
            core_features=entity.core_features,
            feature_priorities=entity.feature_priorities,
            development_phases=entity.development_phases,
            estimated_timeline=entity.estimated_timeline,
            technical_risks=entity.technical_risks,
            roadmap=entity.roadmap,
            executive_summary=entity.executive_summary,
            planning_metrics=entity.planning_metrics,
            llm_model=entity.llm_model,
            strategy_metadata=entity.strategy_metadata,
        )


class ProductStrategyDetail(ProductStrategyRead):
    evidence: list[ProductStrategyEvidenceRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: ProductStrategy) -> "ProductStrategyDetail":
        base = ProductStrategyRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            evidence=[ProductStrategyEvidenceRead.from_entity(item) for item in entity.evidence],
        )
