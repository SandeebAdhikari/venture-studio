"""Competitor intelligence analysis runs for opportunities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import CompetitorAnalysisStatus

if TYPE_CHECKING:
    from app.db.models.competitor_profile import CompetitorProfile
    from app.db.models.opportunity import Opportunity


class CompetitorAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "competitor_analyses"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[CompetitorAnalysisStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=CompetitorAnalysisStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    competitive_gaps: Mapped[list[dict[str, Any]]] = mapped_column(
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
    analysis_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="competitor_analyses")
    profiles: Mapped[list[CompetitorProfile]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="CompetitorProfile.name",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_competitor_analyses_version"),
        Index("idx_competitor_analyses_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_competitor_analyses_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_competitor_analyses_status", "status"),
    )
