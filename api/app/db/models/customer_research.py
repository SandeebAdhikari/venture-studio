"""Customer demand research runs for opportunities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import CustomerResearchStatus

if TYPE_CHECKING:
    from app.db.models.customer_research_evidence import CustomerResearchEvidence
    from app.db.models.opportunity import Opportunity


class CustomerResearch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "customer_research"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[CustomerResearchStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=CustomerResearchStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    pain_score: Mapped[int] = mapped_column(Integer, nullable=False)
    urgency_score: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency_score: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    cares_verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    representative_complaints: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    research_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="customer_research")
    evidence: Mapped[list[CustomerResearchEvidence]] = relationship(
        back_populates="customer_research",
        cascade="all, delete-orphan",
        order_by="CustomerResearchEvidence.created_at",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_customer_research_version"),
        CheckConstraint(
            "pain_score >= 0 AND pain_score <= 100",
            name="ck_customer_research_pain_score",
        ),
        CheckConstraint(
            "urgency_score >= 0 AND urgency_score <= 100",
            name="ck_customer_research_urgency_score",
        ),
        CheckConstraint(
            "frequency_score >= 0 AND frequency_score <= 100",
            name="ck_customer_research_frequency_score",
        ),
        CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="ck_customer_research_sentiment_score",
        ),
        Index("idx_customer_research_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_customer_research_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_customer_research_status", "status"),
        Index("idx_customer_research_pain_score", "pain_score"),
    )
