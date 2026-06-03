"""Human proxy evaluations ranking opportunities for founder fit."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import FounderRecommendation, HumanProxyEvaluationStatus

if TYPE_CHECKING:
    from app.db.models.founder_profile import FounderProfile
    from app.db.models.human_proxy_evaluation_evidence import HumanProxyEvaluationEvidence
    from app.db.models.opportunity import Opportunity


class HumanProxyEvaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "human_proxy_evaluations"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    founder_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("founder_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[HumanProxyEvaluationStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=HumanProxyEvaluationStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    founder_fit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    feasibility_score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation: Mapped[FounderRecommendation] = mapped_column(String(20), nullable=False)
    founder_fit_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    implementation_feasibility: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    learning_curve: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    execution_complexity: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    capital_requirements: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    proxy_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="human_proxy_evaluations")
    founder_profile: Mapped[FounderProfile] = relationship(back_populates="evaluations")
    evidence: Mapped[list[HumanProxyEvaluationEvidence]] = relationship(
        back_populates="human_proxy_evaluation",
        cascade="all, delete-orphan",
        order_by="HumanProxyEvaluationEvidence.created_at",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_human_proxy_evaluations_version"),
        CheckConstraint(
            "founder_fit_score >= 0 AND founder_fit_score <= 100",
            name="ck_human_proxy_evaluations_founder_fit",
        ),
        CheckConstraint(
            "feasibility_score >= 0 AND feasibility_score <= 100",
            name="ck_human_proxy_evaluations_feasibility",
        ),
        Index("idx_human_proxy_evaluations_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_human_proxy_evaluations_current",
            "opportunity_id",
            "founder_profile_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_human_proxy_evaluations_status", "status"),
        Index("idx_human_proxy_evaluations_founder_fit", "founder_fit_score"),
        Index("idx_human_proxy_evaluations_feasibility", "feasibility_score"),
        Index("idx_human_proxy_evaluations_profile", "founder_profile_id"),
    )
