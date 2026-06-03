"""Pydantic schemas for reports."""

from typing import Any
from uuid import UUID

from pydantic import Field

from app.db.enums import ReportStatus, ReportType
from app.schemas.common import ORMModel, UUIDSchema


class ReportBase(ORMModel):
    report_type: ReportType
    title: str = Field(max_length=200)
    summary: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    status: ReportStatus = ReportStatus.DRAFT
    report_metadata: dict[str, Any] = Field(default_factory=dict)


class ReportCreate(ReportBase):
    opportunity_id: UUID | None = None


class ReportUpdate(ORMModel):
    opportunity_id: UUID | None = None
    report_type: ReportType | None = None
    title: str | None = Field(default=None, max_length=200)
    summary: str | None = None
    content: dict[str, Any] | None = None
    status: ReportStatus | None = None
    report_metadata: dict[str, Any] | None = None


class ReportRead(ReportBase, UUIDSchema):
    opportunity_id: UUID | None = None
