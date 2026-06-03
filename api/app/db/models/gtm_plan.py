"""Go-to-market plans for opportunities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import GTMPlanStatus

if TYPE_CHECKING:
    from app.db.models.gtm_plan_evidence import GTMPlanEvidence
    from app.db.models.opportunity import Opportunity


class GTMPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "gtm_plans"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[GTMPlanStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=GTMPlanStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    ideal_customer_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    customer_personas: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    acquisition_channels: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    outreach_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    content_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    seo_opportunities: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    partnerships: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    first_100_customers_plan: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    gtm_report: Mapped[str] = mapped_column(Text, nullable=False)
    acquisition_roadmap: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    estimated_cac_usd: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    ranking_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    gtm_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="gtm_plans")
    evidence: Mapped[list[GTMPlanEvidence]] = relationship(
        back_populates="gtm_plan",
        cascade="all, delete-orphan",
        order_by="GTMPlanEvidence.created_at",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_gtm_plans_version"),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_gtm_plans_confidence_score",
        ),
        CheckConstraint("estimated_cac_usd >= 0", name="ck_gtm_plans_estimated_cac"),
        Index("idx_gtm_plans_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_gtm_plans_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_gtm_plans_status", "status"),
        Index("idx_gtm_plans_confidence", "confidence_score"),
        Index("idx_gtm_plans_cac", "estimated_cac_usd"),
    )
