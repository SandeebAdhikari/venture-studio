"""Report service."""

from uuid import UUID

from app.exceptions import NotFoundError, ValidationError
from app.repositories import RepositoryContainer
from app.schemas.filters import ReportListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate


class ReportService:
    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def list_reports(
        self,
        filters: ReportListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ReportRead]:
        items = await self._repos.reports.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.reports.count_filtered(filters)
        return PaginatedResponse[ReportRead](
            items=[ReportRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_report(self, report_id: UUID) -> ReportRead:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)
        return ReportRead.model_validate(entity)

    async def create_report(self, data: ReportCreate) -> ReportRead:
        if data.opportunity_id is not None:
            if not await self._repos.reports.opportunity_exists(data.opportunity_id):
                raise ValidationError(f"Opportunity '{data.opportunity_id}' does not exist")
        entity = await self._repos.reports.create(data)
        return ReportRead.model_validate(entity)

    async def update_report(self, report_id: UUID, data: ReportUpdate) -> ReportRead:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)
        if data.opportunity_id is not None:
            if not await self._repos.reports.opportunity_exists(data.opportunity_id):
                raise ValidationError(f"Opportunity '{data.opportunity_id}' does not exist")
        entity = await self._repos.reports.update(entity, data)
        return ReportRead.model_validate(entity)

    async def publish_report(self, report_id: UUID) -> ReportRead:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)
        entity = await self._repos.reports.publish(entity)
        return ReportRead.model_validate(entity)

    async def delete_report(self, report_id: UUID) -> None:
        entity = await self._repos.reports.get_by_id(report_id)
        if entity is None:
            raise NotFoundError("report", report_id)
        await self._repos.reports.delete(entity)
