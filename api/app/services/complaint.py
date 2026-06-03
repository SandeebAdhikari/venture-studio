"""Complaint service."""

from uuid import UUID

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.repositories import RepositoryContainer
from app.schemas.category import CategorySummary
from app.schemas.complaint import ComplaintCreate, ComplaintDetail, ComplaintRead, ComplaintUpdate
from app.schemas.filters import ComplaintListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams


class ComplaintService:
    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def list_complaints(
        self,
        filters: ComplaintListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ComplaintRead]:
        items = await self._repos.complaints.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.complaints.count_filtered(filters)
        return PaginatedResponse[ComplaintRead](
            items=[ComplaintRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_complaint(self, complaint_id: UUID) -> ComplaintDetail:
        entity = await self._repos.complaints.get_by_id_with_relations(complaint_id)
        if entity is None:
            raise NotFoundError("complaint", complaint_id)
        return ComplaintDetail(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            signal_id=entity.signal_id,
            category_id=entity.category_id,
            domain_id=entity.domain_id,
            persona_id=entity.persona_id,
            summary=entity.summary,
            verbatim_quote=entity.verbatim_quote,
            severity=entity.severity,
            product_mentions=entity.product_mentions,
            llm_model=entity.llm_model,
            llm_confidence=entity.llm_confidence,
            embedding=entity.embedding,
            category=CategorySummary.model_validate(entity.category),
            domain=CategorySummary.model_validate(entity.domain),
            persona=CategorySummary.model_validate(entity.persona),
        )

    async def create_complaint(self, data: ComplaintCreate) -> ComplaintRead:
        if not await self._repos.complaints.signal_exists(data.signal_id):
            raise ValidationError(f"Signal '{data.signal_id}' does not exist")
        existing = await self._repos.complaints.get_by_signal_id(data.signal_id)
        if existing is not None:
            raise ConflictError(f"Complaint already exists for signal '{data.signal_id}'")
        for label, category_id in (
            ("category", data.category_id),
            ("domain", data.domain_id),
            ("persona", data.persona_id),
        ):
            if await self._repos.categories.get_by_id(category_id) is None:
                raise ValidationError(f"{label} '{category_id}' does not exist")
        entity = await self._repos.complaints.create(data)
        return ComplaintRead.model_validate(entity)

    async def update_complaint(self, complaint_id: UUID, data: ComplaintUpdate) -> ComplaintRead:
        entity = await self._repos.complaints.get_by_id(complaint_id)
        if entity is None:
            raise NotFoundError("complaint", complaint_id)
        for label, category_id in (
            ("category", data.category_id),
            ("domain", data.domain_id),
            ("persona", data.persona_id),
        ):
            if (
                category_id is not None
                and await self._repos.categories.get_by_id(category_id) is None
            ):
                raise ValidationError(f"{label} '{category_id}' does not exist")
        entity = await self._repos.complaints.update(entity, data)
        return ComplaintRead.model_validate(entity)

    async def delete_complaint(self, complaint_id: UUID) -> None:
        entity = await self._repos.complaints.get_by_id(complaint_id)
        if entity is None:
            raise NotFoundError("complaint", complaint_id)
        await self._repos.complaints.delete(entity)
