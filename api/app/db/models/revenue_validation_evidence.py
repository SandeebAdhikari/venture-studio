"""Evidence supporting revenue validation conclusions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.competitor_profile import CompetitorProfile
    from app.db.models.complaint import Complaint
    from app.db.models.revenue_validation import RevenueValidation
    from app.db.models.signal import Signal


class RevenueValidationEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "revenue_validation_evidence"

    revenue_validation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("revenue_validations.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    supports_conclusion: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    complaint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("complaints.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    competitor_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitor_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    revenue_validation: Mapped[RevenueValidation] = relationship(back_populates="evidence")
    complaint: Mapped[Complaint | None] = relationship()
    signal: Mapped[Signal | None] = relationship()
    competitor_profile: Mapped[CompetitorProfile | None] = relationship()

    __table_args__ = (
        Index("idx_revenue_validation_evidence_validation", "revenue_validation_id"),
        Index("idx_revenue_validation_evidence_complaint", "complaint_id"),
    )
