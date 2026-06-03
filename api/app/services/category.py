"""Category service."""

from uuid import UUID

from app.exceptions import ConflictError, NotFoundError
from app.repositories import RepositoryContainer
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.filters import CategoryListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams


class CategoryService:
    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def list_categories(
        self,
        filters: CategoryListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[CategoryRead]:
        items = await self._repos.categories.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.categories.count_filtered(filters)
        return PaginatedResponse[CategoryRead](
            items=[CategoryRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_category(self, category_id: UUID) -> CategoryRead:
        entity = await self._repos.categories.get_by_id(category_id)
        if entity is None:
            raise NotFoundError("category", category_id)
        return CategoryRead.model_validate(entity)

    async def create_category(self, data: CategoryCreate) -> CategoryRead:
        existing = await self._repos.categories.get_by_code_and_kind(data.code, data.kind)
        if existing is not None:
            raise ConflictError(
                f"Category with code '{data.code}' and kind '{data.kind.value}' already exists"
            )
        entity = await self._repos.categories.create(data)
        return CategoryRead.model_validate(entity)

    async def update_category(self, category_id: UUID, data: CategoryUpdate) -> CategoryRead:
        entity = await self._repos.categories.get_by_id(category_id)
        if entity is None:
            raise NotFoundError("category", category_id)
        entity = await self._repos.categories.update(entity, data)
        return CategoryRead.model_validate(entity)
