"""Approval decision repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.approval_decision import ApprovalDecision
from app.repositories.base import BaseRepository
from app.schemas.approval import ApprovalDecisionCreate


class ApprovalDecisionRepository(BaseRepository[ApprovalDecision]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ApprovalDecision)

    async def list_for_request(self, approval_request_id: UUID) -> list[ApprovalDecision]:
        result = await self.session.execute(
            select(ApprovalDecision)
            .where(ApprovalDecision.approval_request_id == approval_request_id)
            .order_by(ApprovalDecision.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        approval_request_id: UUID,
        data: ApprovalDecisionCreate,
    ) -> ApprovalDecision:
        entity = ApprovalDecision(
            approval_request_id=approval_request_id,
            decision_type=data.decision_type.value,
            comment=data.comment,
            actor=data.actor,
            metadata_=data.metadata,
        )
        return await self.add(entity)
