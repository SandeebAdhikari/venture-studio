"""Approval request repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ApprovalStatus, ApprovalSubjectType
from app.db.models.approval_request import ApprovalRequest
from app.repositories.base import BaseRepository
from app.schemas.approval import ApprovalListFilter


class ApprovalRequestRepository(BaseRepository[ApprovalRequest]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ApprovalRequest)

    def _apply_filters(self, query, filters: ApprovalListFilter):
        if filters.status is not None:
            query = query.where(ApprovalRequest.status == filters.status.value)
        if filters.subject_type is not None:
            query = query.where(ApprovalRequest.subject_type == filters.subject_type.value)
        return query

    async def get_by_id_with_decisions(self, entity_id: UUID) -> ApprovalRequest | None:
        result = await self.session.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.decisions))
            .where(ApprovalRequest.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_executive_ranking_run_id(self, run_id: UUID) -> ApprovalRequest | None:
        result = await self.session.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.decisions))
            .where(ApprovalRequest.executive_ranking_run_id == run_id)
            .order_by(ApprovalRequest.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_report_id(self, report_id: UUID) -> ApprovalRequest | None:
        result = await self.session.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.decisions))
            .where(ApprovalRequest.report_id == report_id)
            .order_by(ApprovalRequest.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        filters: ApprovalListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ApprovalRequest]:
        query = self._apply_filters(select(ApprovalRequest), filters)
        result = await self.session.execute(
            query.options(selectinload(ApprovalRequest.decisions))
            .order_by(ApprovalRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: ApprovalListFilter) -> int:
        query = self._apply_filters(select(func.count()).select_from(ApprovalRequest), filters)
        result = await self.session.scalar(query)
        return int(result or 0)

    async def count_by_status(self) -> dict[str, int]:
        result = await self.session.execute(
            select(ApprovalRequest.status, func.count())
            .select_from(ApprovalRequest)
            .group_by(ApprovalRequest.status)
        )
        return {str(status): int(count) for status, count in result.all()}

    async def create(
        self,
        *,
        subject_type: ApprovalSubjectType,
        title: str,
        executive_ranking_run_id: UUID | None = None,
        report_id: UUID | None = None,
    ) -> ApprovalRequest:
        entity = ApprovalRequest(
            subject_type=subject_type.value,
            title=title,
            status=ApprovalStatus.PENDING.value,
            executive_ranking_run_id=executive_ranking_run_id,
            report_id=report_id,
            audit_trail=[],
        )
        return await self.add(entity)

    async def set_status(self, entity: ApprovalRequest, status: ApprovalStatus) -> ApprovalRequest:
        entity.status = status.value
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def append_audit_event(
        self,
        entity: ApprovalRequest,
        event: dict[str, Any],
    ) -> ApprovalRequest:
        trail = list(entity.audit_trail or [])
        trail.append({**event, "timestamp": datetime.now(UTC).isoformat()})
        entity.audit_trail = trail
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
