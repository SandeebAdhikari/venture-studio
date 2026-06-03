"""Market brief repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import MarketResearchStatus
from app.db.models.market_brief import MarketBrief
from app.db.models.opportunity import Opportunity
from app.repositories.base import BaseRepository
from app.schemas.filters import MarketBriefListFilter
from app.schemas.market_brief import MarketBriefCreate


class MarketBriefRepository(BaseRepository[MarketBrief]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketBrief)

    def _apply_filters(self, query, filters: MarketBriefListFilter):
        if filters.opportunity_id is not None:
            query = query.where(MarketBrief.opportunity_id == filters.opportunity_id)
        if filters.status is not None:
            query = query.where(MarketBrief.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(MarketBrief.is_current.is_(filters.is_current))
        return query

    async def get_current_for_opportunity(self, opportunity_id: UUID) -> MarketBrief | None:
        result = await self.session.execute(
            select(MarketBrief).where(
                MarketBrief.opportunity_id == opportunity_id,
                MarketBrief.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[MarketBrief]:
        result = await self.session.execute(
            select(MarketBrief)
            .where(MarketBrief.opportunity_id == opportunity_id)
            .order_by(MarketBrief.version.desc(), MarketBrief.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: MarketBriefListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MarketBrief]:
        query = self._apply_filters(select(MarketBrief), filters)
        result = await self.session.execute(
            query.order_by(MarketBrief.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: MarketBriefListFilter) -> int:
        query = self._apply_filters(select(func.count()).select_from(MarketBrief), filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_research(self, *, limit: int) -> list[UUID]:
        researched_subq = select(MarketBrief.opportunity_id).where(
            MarketBrief.is_current.is_(True),
            MarketBrief.status == MarketResearchStatus.COMPLETED.value,
        )
        result = await self.session.execute(
            select(Opportunity.id)
            .where(Opportunity.id.not_in(researched_subq))
            .order_by(Opportunity.created_at.asc())
            .limit(limit)
        )
        return [row[0] for row in result.all()]

    async def list_opportunity_ids(self, *, limit: int) -> list[UUID]:
        result = await self.session.execute(
            select(Opportunity.id).order_by(Opportunity.created_at.asc()).limit(limit)
        )
        return [row[0] for row in result.all()]

    async def create(self, data: MarketBriefCreate) -> MarketBrief:
        await self.session.execute(
            update(MarketBrief)
            .where(
                MarketBrief.opportunity_id == data.opportunity_id,
                MarketBrief.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(MarketBrief.version)).where(
                MarketBrief.opportunity_id == data.opportunity_id
            )
        )
        next_version = int(current_version or 0) + 1

        entity = MarketBrief(
            opportunity_id=data.opportunity_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            market_size_usd=data.market_size_usd,
            tam_usd=data.tam_usd,
            sam_usd=data.sam_usd,
            industry_growth_rate_pct=data.industry_growth_rate_pct,
            customer_segments=data.customer_segments,
            industry_trends=data.industry_trends,
            supporting_evidence=data.supporting_evidence,
            executive_summary=data.executive_summary,
            llm_model=data.llm_model,
            research_metadata=data.research_metadata,
        )
        return await self.add(entity)
