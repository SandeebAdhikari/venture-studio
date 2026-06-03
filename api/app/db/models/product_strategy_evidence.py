"""Evidence supporting product strategy decisions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.complaint import Complaint
    from app.db.models.product_strategy import ProductStrategy
    from app.db.models.signal import Signal


class ProductStrategyEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_strategy_evidence"

    product_strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_strategies.id", ondelete="CASCADE"),
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

    product_strategy: Mapped[ProductStrategy] = relationship(back_populates="evidence")
    complaint: Mapped[Complaint | None] = relationship()
    signal: Mapped[Signal | None] = relationship()

    __table_args__ = (
        Index("idx_product_strategy_evidence_strategy", "product_strategy_id"),
        Index("idx_product_strategy_evidence_complaint", "complaint_id"),
    )
