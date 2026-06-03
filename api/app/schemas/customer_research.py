"""Customer research persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import CustomerResearchStatus, ReviewSentiment
from app.db.models.customer_research import CustomerResearch
from app.db.models.customer_research_evidence import CustomerResearchEvidence


class CustomerResearchEvidenceCreate(BaseModel):
    evidence_type: str
    excerpt: str
    source_reference: str
    url: str | None = None
    supports_conclusion: str
    confidence: str
    complaint_id: UUID | None = None
    signal_id: UUID | None = None


class CustomerResearchCreate(BaseModel):
    opportunity_id: UUID
    status: CustomerResearchStatus = CustomerResearchStatus.COMPLETED
    pain_score: int = Field(ge=0, le=100)
    urgency_score: int = Field(ge=0, le=100)
    frequency_score: int = Field(ge=0, le=100)
    customer_sentiment: str
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    cares_verdict: str
    representative_complaints: list[dict[str, Any]] = Field(default_factory=list)
    executive_summary: str | None = None
    validation_metrics: dict[str, Any] = Field(default_factory=dict)
    llm_model: str
    research_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[CustomerResearchEvidenceCreate] = Field(default_factory=list)


class CustomerResearchEvidenceRead(BaseModel):
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
    def from_entity(cls, entity: CustomerResearchEvidence) -> "CustomerResearchEvidenceRead":
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


class CustomerResearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    version: int
    status: CustomerResearchStatus
    is_current: bool
    pain_score: int
    urgency_score: int
    frequency_score: int
    customer_sentiment: ReviewSentiment
    sentiment_score: float
    cares_verdict: str
    representative_complaints: list[dict[str, Any]]
    executive_summary: str | None
    validation_metrics: dict[str, Any]
    llm_model: str
    research_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: CustomerResearch) -> "CustomerResearchRead":
        return cls(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            version=entity.version,
            status=CustomerResearchStatus(entity.status),
            is_current=entity.is_current,
            pain_score=entity.pain_score,
            urgency_score=entity.urgency_score,
            frequency_score=entity.frequency_score,
            customer_sentiment=ReviewSentiment(entity.customer_sentiment),
            sentiment_score=entity.sentiment_score,
            cares_verdict=entity.cares_verdict,
            representative_complaints=entity.representative_complaints,
            executive_summary=entity.executive_summary,
            validation_metrics=entity.validation_metrics,
            llm_model=entity.llm_model,
            research_metadata=entity.research_metadata,
        )


class CustomerResearchDetail(CustomerResearchRead):
    evidence: list[CustomerResearchEvidenceRead] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, entity: CustomerResearch) -> "CustomerResearchDetail":
        base = CustomerResearchRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            evidence=[CustomerResearchEvidenceRead.from_entity(item) for item in entity.evidence],
        )
