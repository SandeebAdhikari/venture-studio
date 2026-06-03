"""Report repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ReportStatus, ReportType
from app.db.models.opportunity import Opportunity
from app.db.models.report import Report
from app.repositories.base import BaseRepository
from app.schemas.filters import ReportListFilter
from app.schemas.report import ReportCreate, ReportUpdate


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Report)

    def _apply_filters(self, query, filters: ReportListFilter):
        if filters.opportunity_id is not None:
            query = query.where(Report.opportunity_id == filters.opportunity_id)
        if filters.report_type is not None:
            query = query.where(Report.report_type == filters.report_type.value)
        if filters.status is not None:
            query = query.where(Report.status == filters.status.value)
        return query

    async def list_filtered(
        self,
        filters: ReportListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Report]:
        query = self._apply_filters(select(Report), filters)
        result = await self.session.execute(
            query.order_by(Report.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: ReportListFilter) -> int:
        query = self._apply_filters(select(func.count()).select_from(Report), filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def opportunity_exists(self, opportunity_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(Opportunity).where(Opportunity.id == opportunity_id)
        )
        return int(result.scalar_one()) > 0

    async def list_by_opportunity(self, opportunity_id: UUID) -> list[Report]:
        result = await self.session.execute(
            select(Report)
            .where(Report.opportunity_id == opportunity_id)
            .order_by(Report.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_type(
        self,
        report_type: ReportType,
        *,
        status: ReportStatus | None = None,
        limit: int = 50,
    ) -> list[Report]:
        query = select(Report).where(Report.report_type == report_type.value)
        if status is not None:
            query = query.where(Report.status == status.value)
        result = await self.session.execute(query.order_by(Report.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def create(self, data: ReportCreate) -> Report:
        entity = Report(
            opportunity_id=data.opportunity_id,
            report_type=data.report_type.value,
            title=data.title,
            summary=data.summary,
            content=data.content,
            status=data.status.value,
            report_metadata=data.report_metadata,
        )
        return await self.add(entity)

    async def update(self, entity: Report, data: ReportUpdate) -> Report:
        updates = data.model_dump(exclude_unset=True)
        if "report_type" in updates and updates["report_type"] is not None:
            updates["report_type"] = updates["report_type"].value
        if "status" in updates and updates["status"] is not None:
            updates["status"] = updates["status"].value
        for field, value in updates.items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def publish(self, entity: Report) -> Report:
        entity.status = ReportStatus.PUBLISHED.value
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
