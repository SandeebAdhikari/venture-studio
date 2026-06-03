"""Generated reports and digests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import ReportStatus, ReportType

if TYPE_CHECKING:
    from app.db.models.opportunity import Opportunity


class Report(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "reports"

    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )
    report_type: Mapped[ReportType] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[ReportStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=ReportStatus.DRAFT.value,
    )
    report_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity | None] = relationship(back_populates="reports")

    __table_args__ = (
        Index("idx_reports_type_status", "report_type", "status"),
        Index("idx_reports_opportunity", "opportunity_id"),
    )
