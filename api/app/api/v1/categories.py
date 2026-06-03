"""Category REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import CategoryKind
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.filters import CategoryListFilter
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/categories", tags=["categories"])


def _category_filters(
    kind: Annotated[CategoryKind | None, Query(description="Filter by taxonomy kind")] = None,
    code: Annotated[str | None, Query(max_length=50, description="Filter by category code")] = None,
) -> CategoryListFilter:
    return CategoryListFilter(kind=kind, code=code)


@router.get(
    "",
    response_model=PaginatedResponse[CategoryRead],
    summary="List categories",
    description="Return taxonomy categories used for complaint classification.",
)
async def list_categories(
    services: Services,
    pagination: Pagination,
    filters: Annotated[CategoryListFilter, Depends(_category_filters)],
) -> PaginatedResponse[CategoryRead]:
    return await services.categories.list_categories(filters, pagination)


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Get category",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Category not found"}},
)
async def get_category(category_id: UUID, services: Services) -> CategoryRead:
    return await services.categories.get_category(category_id)


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    responses={status.HTTP_409_CONFLICT: {"description": "Category already exists"}},
)
async def create_category(data: CategoryCreate, services: Services) -> CategoryRead:
    return await services.categories.create_category(data)


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Update category",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Category not found"}},
)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    services: Services,
) -> CategoryRead:
    return await services.categories.update_category(category_id, data)
