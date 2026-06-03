"""Market intelligence briefs produced for opportunities."""

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
from app.db.enums import MarketResearchStatus

if TYPE_CHECKING:
    from app.db.models.opportunity import Opportunity


class MarketBrief(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "market_briefs"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[MarketResearchStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=MarketResearchStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    market_size_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    tam_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    sam_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    industry_growth_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    customer_segments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    industry_trends: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    supporting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    research_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="market_briefs")

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_market_briefs_version"),
        CheckConstraint(
            "industry_growth_rate_pct IS NULL OR "
            "(industry_growth_rate_pct >= -50 AND industry_growth_rate_pct <= 100)",
            name="ck_market_briefs_growth_rate",
        ),
        CheckConstraint(
            "market_size_usd IS NULL OR market_size_usd >= 0",
            name="ck_market_briefs_market_size",
        ),
        CheckConstraint(
            "tam_usd IS NULL OR tam_usd >= 0",
            name="ck_market_briefs_tam",
        ),
        CheckConstraint(
            "sam_usd IS NULL OR sam_usd >= 0",
            name="ck_market_briefs_sam",
        ),
        Index("idx_market_briefs_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_market_briefs_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_market_briefs_status", "status"),
    )
