"""Pydantic schemas for opportunities."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.db.enums import ReviewStatus
from app.schemas.common import ORMModel, UUIDSchema


class OpportunityBase(ORMModel):
    title: str = Field(max_length=200)
    problem_statement: str
    target_user: str
    frequency_signal: str
    existing_alternatives: str
    gap: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    llm_model: str = Field(max_length=50)


class OpportunityCreate(OpportunityBase):
    complaint_ids: list[UUID] = Field(default_factory=list)


class OpportunityUpdate(ORMModel):
    title: str | None = Field(default=None, max_length=200)
    problem_statement: str | None = None
    target_user: str | None = None
    frequency_signal: str | None = None
    existing_alternatives: str | None = None
    gap: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    review_status: ReviewStatus | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    llm_model: str | None = Field(default=None, max_length=50)


class OpportunityRead(OpportunityBase, UUIDSchema):
    review_status: ReviewStatus
    reviewed_at: datetime | None = None
    review_notes: str | None = None


class OpportunityDetail(OpportunityRead):
    complaint_ids: list[UUID] = Field(default_factory=list)
