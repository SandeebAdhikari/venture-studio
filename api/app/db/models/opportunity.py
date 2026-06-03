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
    from app.db.models.complaint import Complaint
    from app.db.models.opportunity_score import OpportunityScore
    from app.db.models.report import Report


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
