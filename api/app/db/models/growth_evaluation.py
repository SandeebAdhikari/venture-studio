"""Long-term growth evaluations for opportunities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import GrowthEvaluationStatus

if TYPE_CHECKING:
    from app.db.models.growth_evaluation_evidence import GrowthEvaluationEvidence
    from app.db.models.opportunity import Opportunity


class GrowthEvaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "growth_evaluations"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[GrowthEvaluationStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=GrowthEvaluationStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    growth_score: Mapped[int] = mapped_column(Integer, nullable=False)
    scalability_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    seo_potential: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    referral_potential: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    partnership_opportunities: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    paid_acquisition_potential: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    market_expansion_opportunities: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    growth_roadmap: Mapped[list[dict[str, Any]]] = mapped_column(
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
    evaluation_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="growth_evaluations")
    evidence: Mapped[list[GrowthEvaluationEvidence]] = relationship(
        back_populates="growth_evaluation",
        cascade="all, delete-orphan",
        order_by="GrowthEvaluationEvidence.created_at",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_growth_evaluations_version"),
        CheckConstraint(
            "growth_score >= 0 AND growth_score <= 100",
            name="ck_growth_evaluations_growth_score",
        ),
        CheckConstraint(
            "scalability_score >= 0 AND scalability_score <= 100",
            name="ck_growth_evaluations_scalability_score",
        ),
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_growth_evaluations_risk_score",
        ),
        Index("idx_growth_evaluations_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_growth_evaluations_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_growth_evaluations_status", "status"),
        Index("idx_growth_evaluations_growth_score", "growth_score"),
        Index("idx_growth_evaluations_scalability_score", "scalability_score"),
    )
