"""Approval workflow schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import (
    ApprovalDecisionType,
    ApprovalStatus,
    ApprovalSubjectType,
)
from app.schemas.common import UUIDSchema


class ApprovalDecisionCreate(BaseModel):
    decision_type: ApprovalDecisionType
    comment: str | None = None
    actor: str = "founder"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRead(UUIDSchema):
    model_config = ConfigDict(from_attributes=True)

    approval_request_id: UUID
    decision_type: ApprovalDecisionType
    comment: str | None = None
    actor: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")


class ApprovalRequestRead(UUIDSchema):
    model_config = ConfigDict(from_attributes=True)

    subject_type: ApprovalSubjectType
    title: str
    status: ApprovalStatus
    executive_ranking_run_id: UUID | None = None
    report_id: UUID | None = None
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[ApprovalDecisionRead] = Field(default_factory=list)


class ApprovalActionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=5000)


class ApprovalListFilter(BaseModel):
    status: ApprovalStatus | None = None
    subject_type: ApprovalSubjectType | None = None


class ApprovalActionResult(BaseModel):
    approval_request_id: UUID
    status: ApprovalStatus
    decision: ApprovalDecisionRead
    finalized: bool = False
