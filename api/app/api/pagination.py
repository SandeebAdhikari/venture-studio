"""Shared API dependencies for route handlers."""

from typing import Annotated

from fastapi import Depends, Query

from app.schemas.pagination import PaginationParams


def get_pagination_params(
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum items to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


Pagination = Annotated[PaginationParams, Depends(get_pagination_params)]
