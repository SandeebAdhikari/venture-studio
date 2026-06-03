"""Revenue validation repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import RevenueValidationStatus
from app.db.models.opportunity import Opportunity
from app.db.models.revenue_validation import RevenueValidation
from app.db.models.revenue_validation_evidence import RevenueValidationEvidence
from app.repositories.base import BaseRepository
from app.schemas.filters import RevenueValidationListFilter
from app.schemas.revenue_validation import RevenueValidationCreate


class RevenueValidationRepository(BaseRepository[RevenueValidation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RevenueValidation)

    def _apply_filters(self, query, filters: RevenueValidationListFilter):
        if filters.opportunity_id is not None:
            query = query.where(RevenueValidation.opportunity_id == filters.opportunity_id)
        if filters.status is not None:
            query = query.where(RevenueValidation.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(RevenueValidation.is_current.is_(filters.is_current))
        if filters.min_willingness_to_pay is not None:
            query = query.where(
                RevenueValidation.willingness_to_pay_score >= filters.min_willingness_to_pay
            )
        return query

    async def get_current_for_opportunity(self, opportunity_id: UUID) -> RevenueValidation | None:
        result = await self.session.execute(
            select(RevenueValidation).where(
                RevenueValidation.opportunity_id == opportunity_id,
                RevenueValidation.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_evidence(self, entity_id: UUID) -> RevenueValidation | None:
        result = await self.session.execute(
            select(RevenueValidation)
            .options(selectinload(RevenueValidation.evidence))
            .where(RevenueValidation.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[RevenueValidation]:
        result = await self.session.execute(
            select(RevenueValidation)
            .where(RevenueValidation.opportunity_id == opportunity_id)
            .order_by(RevenueValidation.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: RevenueValidationListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RevenueValidation]:
        query = self._apply_filters(select(RevenueValidation), filters)
        result = await self.session.execute(
            query.order_by(RevenueValidation.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: RevenueValidationListFilter) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(RevenueValidation),
            filters,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_validation(self, *, limit: int) -> list[UUID]:
        validated_subq = select(RevenueValidation.opportunity_id).where(
            RevenueValidation.is_current.is_(True),
            RevenueValidation.status == RevenueValidationStatus.COMPLETED.value,
        )
        result = await self.session.execute(
            select(Opportunity.id)
            .where(Opportunity.id.not_in(validated_subq))
            .order_by(Opportunity.created_at.asc())
            .limit(limit)
        )
        return [row[0] for row in result.all()]

    async def list_opportunity_ids(self, *, limit: int) -> list[UUID]:
        result = await self.session.execute(
            select(Opportunity.id).order_by(Opportunity.created_at.asc()).limit(limit)
        )
        return [row[0] for row in result.all()]

    async def create(self, data: RevenueValidationCreate) -> RevenueValidation:
        await self.session.execute(
            update(RevenueValidation)
            .where(
                RevenueValidation.opportunity_id == data.opportunity_id,
                RevenueValidation.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(RevenueValidation.version)).where(
                RevenueValidation.opportunity_id == data.opportunity_id
            )
        )
        next_version = int(current_version or 0) + 1

        entity = RevenueValidation(
            opportunity_id=data.opportunity_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            willingness_to_pay_score=data.willingness_to_pay_score,
            revenue_confidence_score=data.revenue_confidence_score,
            pricing_recommendations=data.pricing_recommendations,
            buyer_profiles=data.buyer_profiles,
            executive_summary=data.executive_summary,
            evaluation_metrics=data.evaluation_metrics,
            llm_model=data.llm_model,
            validation_metadata=data.validation_metadata,
        )
        entity = await self.add(entity)

        for evidence_data in data.evidence:
            evidence = RevenueValidationEvidence(
                revenue_validation_id=entity.id,
                evidence_type=evidence_data.evidence_type,
                excerpt=evidence_data.excerpt,
                source_reference=evidence_data.source_reference,
                url=evidence_data.url,
                supports_conclusion=evidence_data.supports_conclusion,
                confidence=evidence_data.confidence,
                complaint_id=evidence_data.complaint_id,
                signal_id=evidence_data.signal_id,
                competitor_profile_id=evidence_data.competitor_profile_id,
            )
            self.session.add(evidence)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity
