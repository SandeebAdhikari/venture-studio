"""Pydantic schemas for complaints."""

from uuid import UUID

from pydantic import Field

from app.schemas.category import CategorySummary
from app.schemas.common import ORMModel, UUIDSchema


class ComplaintBase(ORMModel):
    category_id: UUID
    domain_id: UUID
    persona_id: UUID
    summary: str
    verbatim_quote: str
    severity: int = Field(ge=1, le=5)
    product_mentions: list[str] = Field(default_factory=list)
    llm_model: str = Field(max_length=50)
    llm_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ComplaintCreate(ComplaintBase):
    signal_id: UUID


class ComplaintUpdate(ORMModel):
    category_id: UUID | None = None
    domain_id: UUID | None = None
    persona_id: UUID | None = None
    summary: str | None = None
    verbatim_quote: str | None = None
    severity: int | None = Field(default=None, ge=1, le=5)
    product_mentions: list[str] | None = None
    embedding: list[float] | None = None
    llm_model: str | None = Field(default=None, max_length=50)
    llm_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ComplaintRead(ComplaintBase, UUIDSchema):
    signal_id: UUID
    embedding: list[float] | None = None


class ComplaintDetail(ComplaintRead):
    category: CategorySummary
    domain: CategorySummary
    persona: CategorySummary


class ComplaintLinkRequest(ORMModel):
    """Attach a complaint as evidence on an opportunity."""

    complaint_id: UUID
