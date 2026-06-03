"""Opportunity repository."""

import re
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ReviewStatus
from app.db.models.associations import opportunity_complaints
from app.db.models.complaint import Complaint
from app.db.models.opportunity import Opportunity
from app.repositories.base import BaseRepository
from app.schemas.filters import OpportunityListFilter
from app.schemas.opportunity import OpportunityCreate, OpportunityUpdate


class OpportunityRepository(BaseRepository[Opportunity]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Opportunity)

    def _apply_filters(self, query, filters: OpportunityListFilter):
        if filters.review_status is not None:
            query = query.where(Opportunity.review_status == filters.review_status.value)
        if filters.min_confidence is not None:
            query = query.where(Opportunity.confidence_score >= filters.min_confidence)
        return query

    async def list_filtered(
        self,
        filters: OpportunityListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Opportunity]:
        query = self._apply_filters(select(Opportunity), filters)
        result = await self.session.execute(
            query.order_by(Opportunity.confidence_score.desc(), Opportunity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: OpportunityListFilter) -> int:
        query = self._apply_filters(select(func.count()).select_from(Opportunity), filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def get_by_id_with_relations(self, entity_id: UUID) -> Opportunity | None:
        result = await self.session.execute(
            select(Opportunity)
            .options(
                selectinload(Opportunity.complaints).selectinload(Complaint.category),
                selectinload(Opportunity.complaints).selectinload(Complaint.domain),
                selectinload(Opportunity.complaints).selectinload(Complaint.persona),
                selectinload(Opportunity.scores),
                selectinload(Opportunity.reports),
            )
            .where(Opportunity.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_by_review_status(
        self,
        review_status: ReviewStatus,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Opportunity]:
        result = await self.session.execute(
            select(Opportunity)
            .where(Opportunity.review_status == review_status.value)
            .order_by(Opportunity.confidence_score.desc(), Opportunity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, data: OpportunityCreate) -> Opportunity:
        entity = Opportunity(
            title=data.title,
            problem_statement=data.problem_statement,
            target_user=data.target_user,
            frequency_signal=data.frequency_signal,
            existing_alternatives=data.existing_alternatives,
            gap=data.gap,
            confidence_score=data.confidence_score,
            llm_model=data.llm_model,
        )
        entity = await self.add(entity)

        if data.complaint_ids:
            await self.link_complaints(entity, data.complaint_ids)

        return entity

    async def update(self, entity: Opportunity, data: OpportunityUpdate) -> Opportunity:
        updates = data.model_dump(exclude_unset=True)
        if "review_status" in updates and updates["review_status"] is not None:
            updates["review_status"] = updates["review_status"].value
        for field, value in updates.items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def link_complaints(
        self,
        entity: Opportunity,
        complaint_ids: list[UUID],
        *,
        replace: bool = False,
    ) -> Opportunity:
        if replace:
            await self.session.execute(
                delete(opportunity_complaints).where(
                    opportunity_complaints.c.opportunity_id == entity.id
                )
            )

        if not complaint_ids:
            await self.session.flush()
            return entity

        result = await self.session.execute(
            select(Complaint.id).where(Complaint.id.in_(complaint_ids))
        )
        valid_ids = [row[0] for row in result.all()]
        if valid_ids:
            await self.session.execute(
                insert(opportunity_complaints),
                [
                    {"opportunity_id": entity.id, "complaint_id": complaint_id}
                    for complaint_id in valid_ids
                ],
            )
        await self.session.flush()
        return entity

    async def set_review_status(
        self,
        entity: Opportunity,
        review_status: ReviewStatus,
        *,
        review_notes: str | None = None,
    ) -> Opportunity:
        from datetime import UTC, datetime

        entity.review_status = review_status.value
        entity.reviewed_at = datetime.now(UTC)
        if review_notes is not None:
            entity.review_notes = review_notes
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def exists_similar_title(self, topic: str) -> bool:
        normalized = re.sub(r"[^a-z0-9]+", " ", topic.lower()).strip()
        if not normalized:
            return False

        result = await self.session.execute(select(Opportunity.title))
        for (title,) in result.all():
            existing = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
            if normalized in existing or existing in normalized:
                return True
        return False
