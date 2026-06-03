"""Human proxy evaluation repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import HumanProxyEvaluationStatus
from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
from app.db.models.human_proxy_evaluation_evidence import HumanProxyEvaluationEvidence
from app.db.models.opportunity import Opportunity
from app.repositories.base import BaseRepository
from app.schemas.filters import HumanProxyEvaluationListFilter
from app.schemas.human_proxy_evaluation import HumanProxyEvaluationCreate


class HumanProxyEvaluationRepository(BaseRepository[HumanProxyEvaluation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HumanProxyEvaluation)

    def _apply_filters(self, query, filters: HumanProxyEvaluationListFilter):
        if filters.opportunity_id is not None:
            query = query.where(HumanProxyEvaluation.opportunity_id == filters.opportunity_id)
        if filters.founder_profile_id is not None:
            query = query.where(
                HumanProxyEvaluation.founder_profile_id == filters.founder_profile_id
            )
        if filters.status is not None:
            query = query.where(HumanProxyEvaluation.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(HumanProxyEvaluation.is_current.is_(filters.is_current))
        if filters.min_founder_fit_score is not None:
            query = query.where(
                HumanProxyEvaluation.founder_fit_score >= filters.min_founder_fit_score
            )
        if filters.min_feasibility_score is not None:
            query = query.where(
                HumanProxyEvaluation.feasibility_score >= filters.min_feasibility_score
            )
        if filters.recommendation is not None:
            query = query.where(HumanProxyEvaluation.recommendation == filters.recommendation.value)
        if filters.min_ranking_score is not None:
            query = query.where(
                HumanProxyEvaluation.evaluation_metrics["ranking_score"].as_integer()
                >= filters.min_ranking_score
            )
        return query

    async def get_current_for_opportunity(
        self,
        opportunity_id: UUID,
        *,
        founder_profile_id: UUID,
    ) -> HumanProxyEvaluation | None:
        result = await self.session.execute(
            select(HumanProxyEvaluation).where(
                HumanProxyEvaluation.opportunity_id == opportunity_id,
                HumanProxyEvaluation.founder_profile_id == founder_profile_id,
                HumanProxyEvaluation.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_evidence(self, entity_id: UUID) -> HumanProxyEvaluation | None:
        result = await self.session.execute(
            select(HumanProxyEvaluation)
            .options(selectinload(HumanProxyEvaluation.evidence))
            .where(HumanProxyEvaluation.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(
        self,
        opportunity_id: UUID,
        *,
        founder_profile_id: UUID,
    ) -> list[HumanProxyEvaluation]:
        result = await self.session.execute(
            select(HumanProxyEvaluation)
            .where(
                HumanProxyEvaluation.opportunity_id == opportunity_id,
                HumanProxyEvaluation.founder_profile_id == founder_profile_id,
            )
            .order_by(
                HumanProxyEvaluation.version.desc(),
                HumanProxyEvaluation.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: HumanProxyEvaluationListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HumanProxyEvaluation]:
        query = self._apply_filters(select(HumanProxyEvaluation), filters)
        result = await self.session.execute(
            query.order_by(
                HumanProxyEvaluation.founder_fit_score.desc(),
                HumanProxyEvaluation.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: HumanProxyEvaluationListFilter) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(HumanProxyEvaluation),
            filters,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_evaluation(
        self,
        *,
        founder_profile_id: UUID,
        limit: int,
    ) -> list[UUID]:
        evaluated_subq = select(HumanProxyEvaluation.opportunity_id).where(
            HumanProxyEvaluation.founder_profile_id == founder_profile_id,
            HumanProxyEvaluation.is_current.is_(True),
            HumanProxyEvaluation.status == HumanProxyEvaluationStatus.COMPLETED.value,
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

    async def create(self, data: HumanProxyEvaluationCreate) -> HumanProxyEvaluation:
        await self.session.execute(
            update(HumanProxyEvaluation)
            .where(
                HumanProxyEvaluation.opportunity_id == data.opportunity_id,
                HumanProxyEvaluation.founder_profile_id == data.founder_profile_id,
                HumanProxyEvaluation.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(HumanProxyEvaluation.version)).where(
                HumanProxyEvaluation.opportunity_id == data.opportunity_id,
                HumanProxyEvaluation.founder_profile_id == data.founder_profile_id,
            )
        )
        next_version = int(current_version or 0) + 1

        entity = HumanProxyEvaluation(
            opportunity_id=data.opportunity_id,
            founder_profile_id=data.founder_profile_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            founder_fit_score=data.founder_fit_score,
            feasibility_score=data.feasibility_score,
            recommendation=data.recommendation,
            founder_fit_analysis=data.founder_fit_analysis,
            implementation_feasibility=data.implementation_feasibility,
            learning_curve=data.learning_curve,
            execution_complexity=data.execution_complexity,
            capital_requirements=data.capital_requirements,
            executive_summary=data.executive_summary,
            evaluation_metrics=data.evaluation_metrics,
            llm_model=data.llm_model,
            proxy_metadata=data.proxy_metadata,
        )
        entity = await self.add(entity)

        for evidence_data in data.evidence:
            evidence = HumanProxyEvaluationEvidence(
                human_proxy_evaluation_id=entity.id,
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
