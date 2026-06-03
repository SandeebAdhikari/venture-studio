"""Source REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AppSettings, Services
from app.api.pagination import Pagination
from app.db.enums import SourceType
from app.schemas.filters import SourceListFilter
from app.schemas.pagination import PaginatedResponse
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


def _source_filters(
    enabled: Annotated[bool | None, Query(description="Filter by enabled flag")] = None,
    source_type: Annotated[SourceType | None, Query(description="Filter by source type")] = None,
) -> SourceListFilter:
    return SourceListFilter(enabled=enabled, source_type=source_type)


@router.get(
    "",
    response_model=PaginatedResponse[SourceRead],
    summary="List sources",
    description="Return configured ingestion sources with optional filtering and pagination.",
)
async def list_sources(
    services: Services,
    pagination: Pagination,
    filters: Annotated[SourceListFilter, Depends(_source_filters)],
) -> PaginatedResponse[SourceRead]:
    return await services.sources.list_sources(filters, pagination)


@router.get(
    "/{source_id}",
    response_model=SourceRead,
    summary="Get source",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Source not found"}},
)
async def get_source(source_id: UUID, services: Services) -> SourceRead:
    return await services.sources.get_source(source_id)


@router.post(
    "",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create source",
    responses={status.HTTP_409_CONFLICT: {"description": "Source name already exists"}},
)
async def create_source(data: SourceCreate, services: Services) -> SourceRead:
    return await services.sources.create_source(data)


@router.patch(
    "/{source_id}",
    response_model=SourceRead,
    summary="Update source",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Source not found"},
        status.HTTP_409_CONFLICT: {"description": "Source name already exists"},
    },
)
async def update_source(
    source_id: UUID,
    data: SourceUpdate,
    services: Services,
) -> SourceRead:
    return await services.sources.update_source(source_id, data)


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete source",
    description="Hard-delete a source. Disabled in production.",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Deletion disabled in production"},
        status.HTTP_404_NOT_FOUND: {"description": "Source not found"},
    },
)
async def delete_source(source_id: UUID, services: Services, settings: AppSettings) -> None:
    await services.sources.delete_source(source_id, settings)
