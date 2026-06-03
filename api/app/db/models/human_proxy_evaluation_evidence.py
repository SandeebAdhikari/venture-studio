"""Evidence supporting human proxy evaluation conclusions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.complaint import Complaint
    from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
    from app.db.models.signal import Signal


class HumanProxyEvaluationEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "human_proxy_evaluation_evidence"

    human_proxy_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("human_proxy_evaluations.id", ondelete="CASCADE"),
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

    human_proxy_evaluation: Mapped[HumanProxyEvaluation] = relationship(back_populates="evidence")
    complaint: Mapped[Complaint | None] = relationship()
    signal: Mapped[Signal | None] = relationship()

    __table_args__ = (
        Index("idx_human_proxy_evaluation_evidence_evaluation", "human_proxy_evaluation_id"),
        Index("idx_human_proxy_evaluation_evidence_complaint", "complaint_id"),
    )
