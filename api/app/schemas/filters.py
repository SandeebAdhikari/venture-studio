"""Query filter schemas for list endpoints."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import CategoryKind, ReportStatus, ReportType, ReviewStatus, SourceType


class SourceListFilter(BaseModel):
    enabled: bool | None = None
    source_type: SourceType | None = None


class CategoryListFilter(BaseModel):
    kind: CategoryKind | None = None
    code: str | None = Field(default=None, max_length=50)


class ComplaintListFilter(BaseModel):
    category_id: UUID | None = None
    domain_id: UUID | None = None
    persona_id: UUID | None = None
    min_severity: int | None = Field(default=None, ge=1, le=5)
    signal_id: UUID | None = None


class OpportunityListFilter(BaseModel):
    review_status: ReviewStatus | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ReportListFilter(BaseModel):
    opportunity_id: UUID | None = None
    report_type: ReportType | None = None
    status: ReportStatus | None = None
