"""Go-to-market plan repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import GTMPlanStatus
from app.db.models.gtm_plan import GTMPlan
from app.db.models.gtm_plan_evidence import GTMPlanEvidence
from app.db.models.opportunity import Opportunity
from app.repositories.base import BaseRepository
from app.schemas.filters import GTMPlanListFilter
from app.schemas.gtm_plan import GTMPlanCreate


class GTMPlanRepository(BaseRepository[GTMPlan]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GTMPlan)

    def _apply_filters(self, query, filters: GTMPlanListFilter):
        if filters.opportunity_id is not None:
            query = query.where(GTMPlan.opportunity_id == filters.opportunity_id)
        if filters.status is not None:
            query = query.where(GTMPlan.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(GTMPlan.is_current.is_(filters.is_current))
        if filters.min_confidence_score is not None:
            query = query.where(GTMPlan.confidence_score >= filters.min_confidence_score)
        if filters.max_estimated_cac_usd is not None:
            query = query.where(GTMPlan.estimated_cac_usd <= filters.max_estimated_cac_usd)
        if filters.min_gtm_readiness_score is not None:
            query = query.where(
                GTMPlan.ranking_metrics["gtm_readiness_score"].as_integer()
                >= filters.min_gtm_readiness_score
            )
        return query

    async def get_current_for_opportunity(self, opportunity_id: UUID) -> GTMPlan | None:
        result = await self.session.execute(
            select(GTMPlan).where(
                GTMPlan.opportunity_id == opportunity_id,
                GTMPlan.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_evidence(self, entity_id: UUID) -> GTMPlan | None:
        result = await self.session.execute(
            select(GTMPlan)
            .options(selectinload(GTMPlan.evidence))
            .where(GTMPlan.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[GTMPlan]:
        result = await self.session.execute(
            select(GTMPlan)
            .where(GTMPlan.opportunity_id == opportunity_id)
            .order_by(GTMPlan.version.desc(), GTMPlan.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: GTMPlanListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GTMPlan]:
        query = self._apply_filters(select(GTMPlan), filters)
        result = await self.session.execute(
            query.order_by(GTMPlan.confidence_score.desc(), GTMPlan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: GTMPlanListFilter) -> int:
        query = self._apply_filters(select(func.count()).select_from(GTMPlan), filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_plan(self, *, limit: int) -> list[UUID]:
        planned_subq = select(GTMPlan.opportunity_id).where(
            GTMPlan.is_current.is_(True),
            GTMPlan.status == GTMPlanStatus.COMPLETED.value,
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

    async def create(self, data: GTMPlanCreate) -> GTMPlan:
        await self.session.execute(
            update(GTMPlan)
            .where(
                GTMPlan.opportunity_id == data.opportunity_id,
                GTMPlan.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(GTMPlan.version)).where(GTMPlan.opportunity_id == data.opportunity_id)
        )
        next_version = int(current_version or 0) + 1

        entity = GTMPlan(
            opportunity_id=data.opportunity_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            ideal_customer_profile=data.ideal_customer_profile,
            customer_personas=data.customer_personas,
            acquisition_channels=data.acquisition_channels,
            outreach_strategy=data.outreach_strategy,
            content_strategy=data.content_strategy,
            seo_opportunities=data.seo_opportunities,
            partnerships=data.partnerships,
            first_100_customers_plan=data.first_100_customers_plan,
            gtm_report=data.gtm_report,
            acquisition_roadmap=data.acquisition_roadmap,
            estimated_cac_usd=data.estimated_cac_usd,
            confidence_score=data.confidence_score,
            ranking_metrics=data.ranking_metrics,
            llm_model=data.llm_model,
            gtm_metadata=data.gtm_metadata,
        )
        entity = await self.add(entity)

        for evidence_data in data.evidence:
            evidence = GTMPlanEvidence(
                gtm_plan_id=entity.id,
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
