"""Go-to-market plan persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import GTMPlanStatus
from app.db.models.gtm_plan import GTMPlan
from app.db.models.gtm_plan_evidence import GTMPlanEvidence


class GTMPlanEvidenceCreate(BaseModel):
    evidence_type: str
    excerpt: str
    source_reference: str
    url: str | None = None
    supports_conclusion: str
    confidence: str
    complaint_id: UUID | None = None
    signal_id: UUID | None = None


class GTMPlanCreate(BaseModel):
    opportunity_id: UUID
    status: GTMPlanStatus = GTMPlanStatus.COMPLETED
    ideal_customer_profile: dict[str, Any] = Field(default_factory=dict)
    customer_personas: list[dict[str, Any]] = Field(default_factory=list)
    acquisition_channels: list[dict[str, Any]] = Field(default_factory=list)
    outreach_strategy: dict[str, Any] = Field(default_factory=dict)
    content_strategy: dict[str, Any] = Field(default_factory=dict)
    seo_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    partnerships: list[dict[str, Any]] = Field(default_factory=list)
    first_100_customers_plan: dict[str, Any] = Field(default_factory=dict)
    gtm_report: str
    acquisition_roadmap: list[dict[str, Any]] = Field(default_factory=list)
    estimated_cac_usd: float = Field(ge=0)
    confidence_score: int = Field(ge=0, le=100)
    ranking_metrics: dict[str, Any] = Field(default_factory=dict)
    llm_model: str
    gtm_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[GTMPlanEvidenceCreate] = Field(default_factory=list)


class GTMPlanEvidenceRead(BaseModel):
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
    def from_entity(cls, entity: GTMPlanEvidence) -> "GTMPlanEvidenceRead":
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


class GTMPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    version: int
    status: GTMPlanStatus
    is_current: bool
    ideal_customer_profile: dict[str, Any]
    customer_personas: list[dict[str, Any]]
    acquisition_channels: list[dict[str, Any]]
    outreach_strategy: dict[str, Any]
    content_strategy: dict[str, Any]
    seo_opportunities: list[dict[str, Any]]
    partnerships: list[dict[str, Any]]
    first_100_customers_plan: dict[str, Any]
    gtm_report: str
    acquisition_roadmap: list[dict[str, Any]]
    estimated_cac_usd: float
    confidence_score: int
    ranking_metrics: dict[str, Any]
    llm_model: str
    gtm_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: GTMPlan) -> "GTMPlanRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            version=entity.version,
            status=GTMPlanStatus(entity.status),
            is_current=entity.is_current,
            ideal_customer_profile=entity.ideal_customer_profile,
            customer_personas=entity.customer_personas,
            acquisition_channels=entity.acquisition_channels,
            outreach_strategy=entity.outreach_strategy,
            content_strategy=entity.content_strategy,
            seo_opportunities=entity.seo_opportunities,
            partnerships=entity.partnerships,
            first_100_customers_plan=entity.first_100_customers_plan,
            gtm_report=entity.gtm_report,
            acquisition_roadmap=entity.acquisition_roadmap,
            estimated_cac_usd=entity.estimated_cac_usd,
            confidence_score=entity.confidence_score,
            ranking_metrics=entity.ranking_metrics,
            llm_model=entity.llm_model,
            gtm_metadata=entity.gtm_metadata,
        )


class GTMPlanDetail(GTMPlanRead):
    evidence: list[GTMPlanEvidenceRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: GTMPlan) -> "GTMPlanDetail":
        base = GTMPlanRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            evidence=[GTMPlanEvidenceRead.from_entity(item) for item in entity.evidence],
        )
