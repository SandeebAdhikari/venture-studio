"""Product strategy repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ProductStrategyStatus
from app.db.models.opportunity import Opportunity
from app.db.models.product_strategy import ProductStrategy
from app.db.models.product_strategy_evidence import ProductStrategyEvidence
from app.repositories.base import BaseRepository
from app.schemas.filters import ProductStrategyListFilter
from app.schemas.product_strategy import ProductStrategyCreate


class ProductStrategyRepository(BaseRepository[ProductStrategy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductStrategy)

    def _apply_filters(self, query, filters: ProductStrategyListFilter):
        if filters.opportunity_id is not None:
            query = query.where(ProductStrategy.opportunity_id == filters.opportunity_id)
        if filters.status is not None:
            query = query.where(ProductStrategy.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(ProductStrategy.is_current.is_(filters.is_current))
        if filters.min_total_weeks is not None:
            query = query.where(
                ProductStrategy.estimated_timeline["total_weeks"].as_integer()
                >= filters.min_total_weeks
            )
        return query

    async def get_current_for_opportunity(self, opportunity_id: UUID) -> ProductStrategy | None:
        result = await self.session.execute(
            select(ProductStrategy).where(
                ProductStrategy.opportunity_id == opportunity_id,
                ProductStrategy.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_evidence(self, entity_id: UUID) -> ProductStrategy | None:
        result = await self.session.execute(
            select(ProductStrategy)
            .options(selectinload(ProductStrategy.evidence))
            .where(ProductStrategy.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[ProductStrategy]:
        result = await self.session.execute(
            select(ProductStrategy)
            .where(ProductStrategy.opportunity_id == opportunity_id)
            .order_by(ProductStrategy.version.desc(), ProductStrategy.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: ProductStrategyListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProductStrategy]:
        query = self._apply_filters(select(ProductStrategy), filters)
        result = await self.session.execute(
            query.order_by(ProductStrategy.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: ProductStrategyListFilter) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(ProductStrategy),
            filters,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_strategy(self, *, limit: int) -> list[UUID]:
        planned_subq = select(ProductStrategy.opportunity_id).where(
            ProductStrategy.is_current.is_(True),
            ProductStrategy.status == ProductStrategyStatus.COMPLETED.value,
        )
        result = await self.session.execute(
            select(Opportunity.id)
            .where(Opportunity.id.not_in(planned_subq))
            .order_by(Opportunity.created_at.asc())
            .limit(limit)
        )
        return [row[0] for row in result.all()]

    async def list_opportunity_ids(self, *, limit: int) -> list[UUID]:
        result = await self.session.execute(
            select(Opportunity.id).order_by(Opportunity.created_at.asc()).limit(limit)
        )
        return [row[0] for row in result.all()]

    async def create(self, data: ProductStrategyCreate) -> ProductStrategy:
        await self.session.execute(
            update(ProductStrategy)
            .where(
                ProductStrategy.opportunity_id == data.opportunity_id,
                ProductStrategy.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(ProductStrategy.version)).where(
                ProductStrategy.opportunity_id == data.opportunity_id
            )
        )
        next_version = int(current_version or 0) + 1

        entity = ProductStrategy(
            opportunity_id=data.opportunity_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            mvp_definition=data.mvp_definition,
            core_features=data.core_features,
            feature_priorities=data.feature_priorities,
            development_phases=data.development_phases,
            estimated_timeline=data.estimated_timeline,
            technical_risks=data.technical_risks,
            roadmap=data.roadmap,
            executive_summary=data.executive_summary,
            planning_metrics=data.planning_metrics,
            llm_model=data.llm_model,
            strategy_metadata=data.strategy_metadata,
        )
        entity = await self.add(entity)

        for evidence_data in data.evidence:
            evidence = ProductStrategyEvidence(
                product_strategy_id=entity.id,
                evidence_type=evidence_data.evidence_type,
                excerpt=evidence_data.excerpt,
                source_reference=evidence_data.source_reference,
                url=evidence_data.url,
                supports_conclusion=evidence_data.supports_conclusion,
                confidence=evidence_data.confidence,
                complaint_id=evidence_data.complaint_id,
                signal_id=evidence_data.signal_id,
            )
            self.session.add(evidence)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity
