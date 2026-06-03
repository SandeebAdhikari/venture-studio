"""Individual competitor profiles within an analysis run."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import ReviewSentiment

if TYPE_CHECKING:
    from app.db.models.competitor_analysis import CompetitorAnalysis


class CompetitorProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "competitor_profiles"

    competitor_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitor_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    positioning: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_model: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    strengths: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    weaknesses: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    customer_complaints: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    review_sentiment: Mapped[ReviewSentiment] = mapped_column(String(20), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    analysis: Mapped[CompetitorAnalysis] = relationship(back_populates="profiles")

    __table_args__ = (
        CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="ck_competitor_profiles_sentiment_score",
        ),
        Index("idx_competitor_profiles_analysis", "competitor_analysis_id"),
        Index("idx_competitor_profiles_name", "name"),
    )
