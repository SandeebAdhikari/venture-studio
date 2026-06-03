"""Growth evaluation repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import GrowthEvaluationStatus
from app.db.models.growth_evaluation import GrowthEvaluation
from app.db.models.growth_evaluation_evidence import GrowthEvaluationEvidence
from app.db.models.opportunity import Opportunity
from app.repositories.base import BaseRepository
from app.schemas.filters import GrowthEvaluationListFilter
from app.schemas.growth_evaluation import GrowthEvaluationCreate


class GrowthEvaluationRepository(BaseRepository[GrowthEvaluation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GrowthEvaluation)

    def _apply_filters(self, query, filters: GrowthEvaluationListFilter):
        if filters.opportunity_id is not None:
            query = query.where(GrowthEvaluation.opportunity_id == filters.opportunity_id)
        if filters.status is not None:
            query = query.where(GrowthEvaluation.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(GrowthEvaluation.is_current.is_(filters.is_current))
        if filters.min_growth_score is not None:
            query = query.where(GrowthEvaluation.growth_score >= filters.min_growth_score)
        if filters.min_scalability_score is not None:
            query = query.where(
                GrowthEvaluation.scalability_score >= filters.min_scalability_score
            )
        if filters.max_risk_score is not None:
            query = query.where(GrowthEvaluation.risk_score <= filters.max_risk_score)
        if filters.min_growth_readiness_score is not None:
            query = query.where(
                GrowthEvaluation.evaluation_metrics["growth_readiness_score"].as_integer()
                >= filters.min_growth_readiness_score
            )
        return query

    async def get_current_for_opportunity(self, opportunity_id: UUID) -> GrowthEvaluation | None:
        result = await self.session.execute(
            select(GrowthEvaluation).where(
                GrowthEvaluation.opportunity_id == opportunity_id,
                GrowthEvaluation.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_evidence(self, entity_id: UUID) -> GrowthEvaluation | None:
        result = await self.session.execute(
            select(GrowthEvaluation)
            .options(selectinload(GrowthEvaluation.evidence))
            .where(GrowthEvaluation.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[GrowthEvaluation]:
        result = await self.session.execute(
            select(GrowthEvaluation)
            .where(GrowthEvaluation.opportunity_id == opportunity_id)
            .order_by(GrowthEvaluation.version.desc(), GrowthEvaluation.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: GrowthEvaluationListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GrowthEvaluation]:
        query = self._apply_filters(select(GrowthEvaluation), filters)
        result = await self.session.execute(
            query.order_by(GrowthEvaluation.growth_score.desc(), GrowthEvaluation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: GrowthEvaluationListFilter) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(GrowthEvaluation),
            filters,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_evaluation(self, *, limit: int) -> list[UUID]:
        evaluated_subq = select(GrowthEvaluation.opportunity_id).where(
            GrowthEvaluation.is_current.is_(True),
            GrowthEvaluation.status == GrowthEvaluationStatus.COMPLETED.value,
        )
        result = await self.session.execute(
            select(Opportunity.id)
            .where(Opportunity.id.not_in(evaluated_subq))
            .order_by(Opportunity.created_at.asc())
            .limit(limit)
        )
        return [row[0] for row in result.all()]

    async def list_opportunity_ids(self, *, limit: int) -> list[UUID]:
        result = await self.session.execute(
            select(Opportunity.id).order_by(Opportunity.created_at.asc()).limit(limit)
        )
        return [row[0] for row in result.all()]

    async def create(self, data: GrowthEvaluationCreate) -> GrowthEvaluation:
        await self.session.execute(
            update(GrowthEvaluation)
            .where(
                GrowthEvaluation.opportunity_id == data.opportunity_id,
                GrowthEvaluation.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(GrowthEvaluation.version)).where(
                GrowthEvaluation.opportunity_id == data.opportunity_id
            )
        )
        next_version = int(current_version or 0) + 1

        entity = GrowthEvaluation(
            opportunity_id=data.opportunity_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            growth_score=data.growth_score,
            scalability_score=data.scalability_score,
            risk_score=data.risk_score,
            seo_potential=data.seo_potential,
            referral_potential=data.referral_potential,
            partnership_opportunities=data.partnership_opportunities,
            paid_acquisition_potential=data.paid_acquisition_potential,
            market_expansion_opportunities=data.market_expansion_opportunities,
            growth_roadmap=data.growth_roadmap,
            executive_summary=data.executive_summary,
            evaluation_metrics=data.evaluation_metrics,
            llm_model=data.llm_model,
            evaluation_metadata=data.evaluation_metadata,
        )
        entity = await self.add(entity)

        for evidence_data in data.evidence:
            evidence = GrowthEvaluationEvidence(
                growth_evaluation_id=entity.id,
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
