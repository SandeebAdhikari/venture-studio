"""Opportunity service."""

from uuid import UUID

from app.db.enums import ReviewStatus
from app.exceptions import NotFoundError, ValidationError
from app.repositories import RepositoryContainer
from app.schemas.filters import OpportunityListFilter
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityDetail,
    OpportunityRead,
    OpportunityUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams


class OpportunityService:
    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def list_opportunities(
        self,
        filters: OpportunityListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[OpportunityRead]:
        items = await self._repos.opportunities.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.opportunities.count_filtered(filters)
        return PaginatedResponse[OpportunityRead](
            items=[OpportunityRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_opportunity(self, opportunity_id: UUID) -> OpportunityDetail:
        entity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if entity is None:
            raise NotFoundError("opportunity", opportunity_id)
        base = OpportunityRead.model_validate(entity)
        return OpportunityDetail(
            **base.model_dump(),
            complaint_ids=[complaint.id for complaint in entity.complaints],
        )

    async def create_opportunity(self, data: OpportunityCreate) -> OpportunityDetail:
        if data.complaint_ids:
            await self._validate_complaint_ids(data.complaint_ids)
        entity = await self._repos.opportunities.create(data)
        loaded = await self._repos.opportunities.get_by_id_with_relations(entity.id)
        assert loaded is not None
        base = OpportunityRead.model_validate(loaded)
        return OpportunityDetail(
            **base.model_dump(),
            complaint_ids=[complaint.id for complaint in loaded.complaints],
        )

    async def update_opportunity(
        self,
        opportunity_id: UUID,
        data: OpportunityUpdate,
    ) -> OpportunityRead:
        entity = await self._repos.opportunities.get_by_id(opportunity_id)
        if entity is None:
            raise NotFoundError("opportunity", opportunity_id)
        entity = await self._repos.opportunities.update(entity, data)
        return OpportunityRead.model_validate(entity)

    async def set_review_status(
        self,
        opportunity_id: UUID,
        review_status: ReviewStatus,
        *,
        review_notes: str | None = None,
    ) -> OpportunityRead:
        entity = await self._repos.opportunities.get_by_id(opportunity_id)
        if entity is None:
            raise NotFoundError("opportunity", opportunity_id)
        entity = await self._repos.opportunities.set_review_status(
            entity,
            review_status,
            review_notes=review_notes,
        )
        return OpportunityRead.model_validate(entity)

    async def link_complaints(
        self,
        opportunity_id: UUID,
        complaint_ids: list[UUID],
    ) -> OpportunityDetail:
        entity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if entity is None:
            raise NotFoundError("opportunity", opportunity_id)
        if complaint_ids:
            await self._validate_complaint_ids(complaint_ids)
        entity = await self._repos.opportunities.link_complaints(
            entity,
            complaint_ids,
            replace=True,
        )
        loaded = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        assert loaded is not None
        base = OpportunityRead.model_validate(loaded)
        return OpportunityDetail(
            **base.model_dump(),
            complaint_ids=[complaint.id for complaint in loaded.complaints],
        )

    async def _validate_complaint_ids(self, complaint_ids: list[UUID]) -> None:
        for complaint_id in complaint_ids:
            if await self._repos.complaints.get_by_id(complaint_id) is None:
                raise ValidationError(f"Complaint '{complaint_id}' does not exist")
