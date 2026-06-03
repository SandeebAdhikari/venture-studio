"""Business opportunity synthesized from complaint clusters."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import ReviewStatus
from app.db.models.associations import opportunity_complaints

if TYPE_CHECKING:
    from app.db.models.competitor_analysis import CompetitorAnalysis
    from app.db.models.complaint import Complaint
    from app.db.models.customer_research import CustomerResearch
    from app.db.models.growth_evaluation import GrowthEvaluation
    from app.db.models.gtm_plan import GTMPlan
    from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
    from app.db.models.market_brief import MarketBrief
    from app.db.models.opportunity_score import OpportunityScore
    from app.db.models.product_strategy import ProductStrategy
    from app.db.models.report import Report
    from app.db.models.revenue_validation import RevenueValidation


class Opportunity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "opportunities"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    target_user: Mapped[str] = mapped_column(Text, nullable=False)
    frequency_signal: Mapped[str] = mapped_column(Text, nullable=False)
    existing_alternatives: Mapped[str] = mapped_column(Text, nullable=False)
    gap: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=ReviewStatus.NEW.value,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)

    complaints: Mapped[list[Complaint]] = relationship(
        secondary=opportunity_complaints,
        back_populates="opportunities",
    )
    scores: Mapped[list[OpportunityScore]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(OpportunityScore.created_at)",
    )
    reports: Mapped[list[Report]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    market_briefs: Mapped[list[MarketBrief]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(MarketBrief.created_at)",
    )
    competitor_analyses: Mapped[list[CompetitorAnalysis]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(CompetitorAnalysis.created_at)",
    )
    customer_research: Mapped[list[CustomerResearch]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(CustomerResearch.created_at)",
    )
    revenue_validations: Mapped[list[RevenueValidation]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(RevenueValidation.created_at)",
    )
    product_strategies: Mapped[list[ProductStrategy]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(ProductStrategy.created_at)",
    )
    gtm_plans: Mapped[list[GTMPlan]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(GTMPlan.created_at)",
    )
    growth_evaluations: Mapped[list[GrowthEvaluation]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(GrowthEvaluation.created_at)",
    )
    human_proxy_evaluations: Mapped[list[HumanProxyEvaluation]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(HumanProxyEvaluation.created_at)",
    )

    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_opportunities_confidence",
        ),
        Index("idx_opportunities_review_status", "review_status", "created_at"),
        Index(
            "idx_opportunities_confidence",
            "confidence_score",
            postgresql_ops={"confidence_score": "DESC"},
        ),
    )
