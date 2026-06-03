"""Multi-dimensional scores for ranking opportunities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.opportunity import Opportunity


class OpportunityScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "opportunity_scores"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    frequency_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    volume_score: Mapped[float] = mapped_column(Float, nullable=False)
    market_indicator_score: Mapped[float] = mapped_column(Float, nullable=False)
    implementation_ease_score: Mapped[float] = mapped_column(Float, nullable=False)
    founder_fit_score: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_model: Mapped[str] = mapped_column(String(50), nullable=False)
    scoring_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="scores")

    __table_args__ = (
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 1", name="ck_opportunity_scores_overall"
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_opportunity_scores_score"),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_opportunity_scores_confidence",
        ),
        CheckConstraint(
            "frequency_score >= 0 AND frequency_score <= 1",
            name="ck_opportunity_scores_frequency",
        ),
        CheckConstraint(
            "severity_score >= 0 AND severity_score <= 1",
            name="ck_opportunity_scores_severity",
        ),
        CheckConstraint(
            "evidence_score >= 0 AND evidence_score <= 1",
            name="ck_opportunity_scores_evidence",
        ),
        CheckConstraint(
            "volume_score >= 0 AND volume_score <= 1",
            name="ck_opportunity_scores_volume",
        ),
        CheckConstraint(
            "market_indicator_score >= 0 AND market_indicator_score <= 1",
            name="ck_opportunity_scores_market",
        ),
        CheckConstraint(
            "implementation_ease_score >= 0 AND implementation_ease_score <= 1",
            name="ck_opportunity_scores_implementation",
        ),
        CheckConstraint(
            "founder_fit_score >= 0 AND founder_fit_score <= 1",
            name="ck_opportunity_scores_founder_fit",
        ),
        Index("idx_opportunity_scores_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_opportunity_scores_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index(
            "idx_opportunity_scores_overall",
            "overall_score",
            postgresql_ops={"overall_score": "DESC"},
        ),
        Index(
            "idx_opportunity_scores_score",
            "score",
            postgresql_ops={"score": "DESC"},
        ),
    )
