"""Market brief persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import MarketResearchStatus


class MarketBriefCreate(BaseModel):
    opportunity_id: UUID
    status: MarketResearchStatus = MarketResearchStatus.COMPLETED
    market_size_usd: float | None = None
    tam_usd: float | None = None
    sam_usd: float | None = None
    industry_growth_rate_pct: float | None = None
    customer_segments: list[dict[str, Any]] = Field(default_factory=list)
    industry_trends: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    executive_summary: str | None = None
    llm_model: str
    research_metadata: dict[str, Any] = Field(default_factory=dict)


class MarketBriefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    version: int
    status: MarketResearchStatus
    is_current: bool
    market_size_usd: float | None
    tam_usd: float | None
    sam_usd: float | None
    industry_growth_rate_pct: float | None
    customer_segments: list[dict[str, Any]]
    industry_trends: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    executive_summary: str | None
    llm_model: str
    research_metadata: dict[str, Any]
