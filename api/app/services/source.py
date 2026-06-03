"""Source service."""

from uuid import UUID

from app.config import Settings
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories import RepositoryContainer
from app.schemas.filters import SourceListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate


class SourceService:
    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def list_sources(
        self,
        filters: SourceListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[SourceRead]:
        items = await self._repos.sources.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.sources.count_filtered(filters)
        return PaginatedResponse[SourceRead](
            items=[SourceRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_source(self, source_id: UUID) -> SourceRead:
        entity = await self._repos.sources.get_by_id(source_id)
        if entity is None:
            raise NotFoundError("source", source_id)
        return SourceRead.model_validate(entity)

    async def create_source(self, data: SourceCreate) -> SourceRead:
        existing = await self._repos.sources.get_by_name(data.name)
        if existing is not None:
            raise ConflictError(f"Source with name '{data.name}' already exists")
        entity = await self._repos.sources.create(data)
        return SourceRead.model_validate(entity)

    async def update_source(self, source_id: UUID, data: SourceUpdate) -> SourceRead:
        entity = await self._repos.sources.get_by_id(source_id)
        if entity is None:
            raise NotFoundError("source", source_id)
        if data.name is not None:
            duplicate = await self._repos.sources.get_by_name(data.name)
            if duplicate is not None and duplicate.id != source_id:
                raise ConflictError(f"Source with name '{data.name}' already exists")
        entity = await self._repos.sources.update(entity, data)
        return SourceRead.model_validate(entity)

    async def delete_source(self, source_id: UUID, settings: Settings) -> None:
        if settings.is_production:
            raise ForbiddenError("Source deletion is disabled in production")
        entity = await self._repos.sources.get_by_id(source_id)
        if entity is None:
            raise NotFoundError("source", source_id)
        await self._repos.sources.delete(entity)
