"""Revenue validation runs for opportunities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import RevenueValidationStatus

if TYPE_CHECKING:
    from app.db.models.opportunity import Opportunity
    from app.db.models.revenue_validation_evidence import RevenueValidationEvidence


class RevenueValidation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "revenue_validations"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[RevenueValidationStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=RevenueValidationStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    willingness_to_pay_score: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue_confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    pricing_recommendations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    buyer_profiles: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    validation_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="revenue_validations")
    evidence: Mapped[list[RevenueValidationEvidence]] = relationship(
        back_populates="revenue_validation",
        cascade="all, delete-orphan",
        order_by="RevenueValidationEvidence.created_at",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_revenue_validations_version"),
        CheckConstraint(
            "willingness_to_pay_score >= 0 AND willingness_to_pay_score <= 100",
            name="ck_revenue_validations_wtp_score",
        ),
        CheckConstraint(
            "revenue_confidence_score >= 0 AND revenue_confidence_score <= 100",
            name="ck_revenue_validations_confidence_score",
        ),
        Index("idx_revenue_validations_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_revenue_validations_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_revenue_validations_status", "status"),
        Index("idx_revenue_validations_wtp", "willingness_to_pay_score"),
    )
