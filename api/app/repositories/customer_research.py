"""Customer research repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import CustomerResearchStatus
from app.db.models.customer_research import CustomerResearch
from app.db.models.customer_research_evidence import CustomerResearchEvidence
from app.db.models.opportunity import Opportunity
from app.repositories.base import BaseRepository
from app.schemas.customer_research import CustomerResearchCreate
from app.schemas.filters import CustomerResearchListFilter


class CustomerResearchRepository(BaseRepository[CustomerResearch]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CustomerResearch)

    def _apply_filters(self, query, filters: CustomerResearchListFilter):
        if filters.opportunity_id is not None:
            query = query.where(CustomerResearch.opportunity_id == filters.opportunity_id)
        if filters.status is not None:
            query = query.where(CustomerResearch.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(CustomerResearch.is_current.is_(filters.is_current))
        if filters.min_pain_score is not None:
            query = query.where(CustomerResearch.pain_score >= filters.min_pain_score)
        if filters.cares_verdict is not None:
            query = query.where(CustomerResearch.cares_verdict == filters.cares_verdict)
        return query

    async def get_current_for_opportunity(self, opportunity_id: UUID) -> CustomerResearch | None:
        result = await self.session.execute(
            select(CustomerResearch).where(
                CustomerResearch.opportunity_id == opportunity_id,
                CustomerResearch.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_evidence(self, entity_id: UUID) -> CustomerResearch | None:
        result = await self.session.execute(
            select(CustomerResearch)
            .options(selectinload(CustomerResearch.evidence))
            .where(CustomerResearch.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[CustomerResearch]:
        result = await self.session.execute(
            select(CustomerResearch)
            .where(CustomerResearch.opportunity_id == opportunity_id)
            .order_by(CustomerResearch.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: CustomerResearchListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CustomerResearch]:
        query = self._apply_filters(select(CustomerResearch), filters)
        result = await self.session.execute(
            query.order_by(CustomerResearch.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: CustomerResearchListFilter) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(CustomerResearch),
            filters,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_research(self, *, limit: int) -> list[UUID]:
        researched_subq = select(CustomerResearch.opportunity_id).where(
            CustomerResearch.is_current.is_(True),
            CustomerResearch.status == CustomerResearchStatus.COMPLETED.value,
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

    async def create(self, data: CustomerResearchCreate) -> CustomerResearch:
        await self.session.execute(
            update(CustomerResearch)
            .where(
                CustomerResearch.opportunity_id == data.opportunity_id,
                CustomerResearch.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(CustomerResearch.version)).where(
                CustomerResearch.opportunity_id == data.opportunity_id
            )
        )
        next_version = int(current_version or 0) + 1

        entity = CustomerResearch(
            opportunity_id=data.opportunity_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            pain_score=data.pain_score,
            urgency_score=data.urgency_score,
            frequency_score=data.frequency_score,
            customer_sentiment=data.customer_sentiment,
            sentiment_score=data.sentiment_score,
            cares_verdict=data.cares_verdict,
            representative_complaints=data.representative_complaints,
            executive_summary=data.executive_summary,
            validation_metrics=data.validation_metrics,
            llm_model=data.llm_model,
            research_metadata=data.research_metadata,
        )
        entity = await self.add(entity)

        for evidence_data in data.evidence:
            evidence = CustomerResearchEvidence(
                customer_research_id=entity.id,
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
