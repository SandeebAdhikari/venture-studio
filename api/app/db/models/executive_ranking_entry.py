"""Per-opportunity entries within an executive ranking run."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.executive_ranking_run import ExecutiveRankingRun
    from app.db.models.opportunity import Opportunity


class ExecutiveRankingEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "executive_ranking_entries"

    executive_ranking_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executive_ranking_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    final_opportunity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    pain_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competition_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    growth_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    founder_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_coverage_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_top_opportunity: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    source_references: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    ranking_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    ranking_run: Mapped[ExecutiveRankingRun] = relationship(back_populates="entries")
    opportunity: Mapped[Opportunity] = relationship()

    __table_args__ = (
        CheckConstraint("rank >= 1", name="ck_executive_ranking_entries_rank"),
        CheckConstraint(
            "final_opportunity_score >= 0 AND final_opportunity_score <= 100",
            name="ck_executive_ranking_entries_final_score",
        ),
        CheckConstraint(
            "pain_score IS NULL OR (pain_score >= 0 AND pain_score <= 100)",
            name="ck_executive_ranking_entries_pain",
        ),
        CheckConstraint(
            "market_score IS NULL OR (market_score >= 0 AND market_score <= 100)",
            name="ck_executive_ranking_entries_market",
        ),
        CheckConstraint(
            "revenue_score IS NULL OR (revenue_score >= 0 AND revenue_score <= 100)",
            name="ck_executive_ranking_entries_revenue",
        ),
        CheckConstraint(
            "competition_score IS NULL OR (competition_score >= 0 AND competition_score <= 100)",
            name="ck_executive_ranking_entries_competition",
        ),
        CheckConstraint(
            "growth_score IS NULL OR (growth_score >= 0 AND growth_score <= 100)",
            name="ck_executive_ranking_entries_growth",
        ),
        CheckConstraint(
            "founder_fit_score IS NULL OR (founder_fit_score >= 0 AND founder_fit_score <= 100)",
            name="ck_executive_ranking_entries_founder_fit",
        ),
        Index(
            "idx_executive_ranking_entries_run",
            "executive_ranking_run_id",
            "rank",
        ),
        Index(
            "idx_executive_ranking_entries_opportunity",
            "opportunity_id",
            "created_at",
        ),
        Index(
            "idx_executive_ranking_entries_top",
            "executive_ranking_run_id",
            "is_top_opportunity",
        ),
    )
