"""Founder approval request for rankings and venture reports."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.approval_decision import ApprovalDecision
    from app.db.models.executive_ranking_run import ExecutiveRankingRun
    from app.db.models.report import Report


class ApprovalRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "approval_requests"

    subject_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    executive_ranking_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executive_ranking_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=True,
    )
    audit_trail: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default="[]")

    executive_ranking_run: Mapped[ExecutiveRankingRun | None] = relationship()
    report: Mapped[Report | None] = relationship()
    decisions: Mapped[list[ApprovalDecision]] = relationship(
        back_populates="approval_request",
        cascade="all, delete-orphan",
        order_by="ApprovalDecision.created_at",
    )

    __table_args__ = (
        CheckConstraint(
            "(executive_ranking_run_id IS NOT NULL) OR (report_id IS NOT NULL)",
            name="ck_approval_requests_subject",
        ),
        Index("idx_approval_requests_status", "status"),
        Index("idx_approval_requests_subject_type", "subject_type"),
        Index("idx_approval_requests_ranking_run", "executive_ranking_run_id"),
        Index("idx_approval_requests_report", "report_id"),
    )
