"""Founder approval workflow service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from app.config import Settings, get_settings
from app.db.enums import (
    ApprovalDecisionType,
    ApprovalStatus,
    ApprovalSubjectType,
)
from app.exceptions import NotFoundError, ValidationError
from app.repositories import RepositoryContainer
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResult,
    ApprovalDecisionCreate,
    ApprovalDecisionRead,
    ApprovalListFilter,
    ApprovalRequestRead,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams

if TYPE_CHECKING:
    pass


class ApprovalService:
    """Manages founder review before rankings and venture reports are finalized."""

    _ACTIONABLE_STATUSES = {
        ApprovalStatus.PENDING,
        ApprovalStatus.RESEARCH_REQUESTED,
    }

    def __init__(self, repos: RepositoryContainer, settings: Settings | None = None) -> None:
        self._repos = repos
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.require_founder_approval

    async def list_approvals(
        self,
        filters: ApprovalListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ApprovalRequestRead]:
        items = await self._repos.approval_requests.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.approval_requests.count_filtered(filters)
        return PaginatedResponse[ApprovalRequestRead](
            items=[self._to_read(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_approval(self, approval_id: UUID) -> ApprovalRequestRead:
        entity = await self._repos.approval_requests.get_by_id_with_decisions(approval_id)
        if entity is None:
            raise NotFoundError("approval_request", approval_id)
        return self._to_read(entity)

    async def approve(self, approval_id: UUID, data: ApprovalActionRequest) -> ApprovalActionResult:
        return await self._apply_decision(
            approval_id,
            decision_type=ApprovalDecisionType.APPROVE,
            new_status=ApprovalStatus.APPROVED,
            data=data,
        )

    async def reject(self, approval_id: UUID, data: ApprovalActionRequest) -> ApprovalActionResult:
        return await self._apply_decision(
            approval_id,
            decision_type=ApprovalDecisionType.REJECT,
            new_status=ApprovalStatus.REJECTED,
            data=data,
        )

    async def request_research(
        self,
        approval_id: UUID,
        data: ApprovalActionRequest,
    ) -> ApprovalActionResult:
        if not data.comment or not data.comment.strip():
            raise ValidationError("A comment is required when requesting more research.")
        return await self._apply_decision(
            approval_id,
            decision_type=ApprovalDecisionType.REQUEST_RESEARCH,
            new_status=ApprovalStatus.RESEARCH_REQUESTED,
            data=data,
        )

    async def create_for_executive_ranking(
        self,
        *,
        run_id: UUID,
        title: str,
        version: int,
    ) -> ApprovalRequestRead | None:
        if not self.enabled:
            return None

        existing = await self._repos.approval_requests.get_by_executive_ranking_run_id(run_id)
        if existing is not None:
            return self._to_read(existing)

        entity = await self._repos.approval_requests.create(
            subject_type=ApprovalSubjectType.EXECUTIVE_RANKING,
            title=title,
            executive_ranking_run_id=run_id,
        )
        await self._repos.approval_requests.append_audit_event(
            entity,
            {
                "event": "approval_created",
                "subject_type": ApprovalSubjectType.EXECUTIVE_RANKING.value,
                "executive_ranking_run_id": str(run_id),
                "version": version,
            },
        )

        run = await self._repos.executive_rankings.get_by_id(run_id)
        if run is not None:
            metadata = dict(run.ranking_metadata or {})
            metadata.update(
                {
                    "approval_request_id": str(entity.id),
                    "approval_status": ApprovalStatus.PENDING.value,
                }
            )
            run.ranking_metadata = metadata
            await self._repos.session.flush()

        return self._to_read(
            await self._repos.approval_requests.get_by_id_with_decisions(entity.id) or entity
        )

    async def create_for_venture_report(
        self,
        *,
        report_id: UUID,
        title: str,
        executive_ranking_run_id: UUID | None,
    ) -> ApprovalRequestRead | None:
        if not self.enabled:
            return None

        existing = await self._repos.approval_requests.get_by_report_id(report_id)
        if existing is not None:
            return self._to_read(existing)

        entity = await self._repos.approval_requests.create(
            subject_type=ApprovalSubjectType.VENTURE_REPORT,
            title=title,
            report_id=report_id,
        )
        await self._repos.approval_requests.append_audit_event(
            entity,
            {
                "event": "approval_created",
                "subject_type": ApprovalSubjectType.VENTURE_REPORT.value,
                "report_id": str(report_id),
                "executive_ranking_run_id": str(executive_ranking_run_id)
                if executive_ranking_run_id
                else None,
            },
        )

        report = await self._repos.reports.get_by_id(report_id)
        if report is not None:
            metadata = dict(report.report_metadata or {})
            metadata.update(
                {
                    "approval_request_id": str(entity.id),
                    "approval_status": ApprovalStatus.PENDING.value,
                }
            )
            report.report_metadata = metadata
            await self._repos.session.flush()

        return self._to_read(
            await self._repos.approval_requests.get_by_id_with_decisions(entity.id) or entity
        )

    async def _apply_decision(
        self,
        approval_id: UUID,
        *,
        decision_type: ApprovalDecisionType,
        new_status: ApprovalStatus,
        data: ApprovalActionRequest,
    ) -> ApprovalActionResult:
        entity = await self._repos.approval_requests.get_by_id_with_decisions(approval_id)
        if entity is None:
            raise NotFoundError("approval_request", approval_id)

        current_status = ApprovalStatus(entity.status)
        if current_status not in self._ACTIONABLE_STATUSES:
            raise ValidationError(
                f"Approval request '{approval_id}' is in status '{current_status.value}' "
                "and cannot be updated."
            )

        decision = await self._repos.approval_decisions.create(
            entity.id,
            ApprovalDecisionCreate(
                decision_type=decision_type,
                comment=data.comment,
            ),
        )
        entity = await self._repos.approval_requests.set_status(entity, new_status)
        await self._repos.approval_requests.append_audit_event(
            entity,
            {
                "event": f"decision_{decision_type.value}",
                "decision_id": str(decision.id),
                "comment": data.comment,
                "previous_status": current_status.value,
                "new_status": new_status.value,
            },
        )

        finalized = await self._finalize_subject(entity, new_status)

        refreshed = await self._repos.approval_requests.get_by_id_with_decisions(entity.id)
        assert refreshed is not None
        return ApprovalActionResult(
            approval_request_id=refreshed.id,
            status=ApprovalStatus(refreshed.status),
            decision=ApprovalDecisionRead.model_validate(decision),
            finalized=finalized,
        )

    async def _finalize_subject(
        self,
        entity,
        status: ApprovalStatus,
    ) -> bool:
        if status == ApprovalStatus.APPROVED:
            if entity.subject_type == ApprovalSubjectType.VENTURE_REPORT.value and entity.report_id:
                report = await self._repos.reports.get_by_id(entity.report_id)
                if report is not None:
                    await self._repos.reports.publish(report)
                    metadata = dict(report.report_metadata or {})
                    metadata.update(
                        {
                            "approval_status": ApprovalStatus.APPROVED.value,
                            "finalized_at": datetime.now(UTC).isoformat(),
                        }
                    )
                    report.report_metadata = metadata
                    await self._repos.approval_requests.append_audit_event(
                        entity,
                        {"event": "venture_report_published", "report_id": str(report.id)},
                    )
                    return True

            if (
                entity.subject_type == ApprovalSubjectType.EXECUTIVE_RANKING.value
                and entity.executive_ranking_run_id
            ):
                run = await self._repos.executive_rankings.get_by_id(
                    entity.executive_ranking_run_id
                )
                if run is not None:
                    metadata = dict(run.ranking_metadata or {})
                    metadata.update(
                        {
                            "approval_status": ApprovalStatus.APPROVED.value,
                            "finalized_at": datetime.now(UTC).isoformat(),
                        }
                    )
                    run.ranking_metadata = metadata
                    await self._repos.approval_requests.append_audit_event(
                        entity,
                        {
                            "event": "executive_ranking_finalized",
                            "executive_ranking_run_id": str(run.id),
                        },
                    )
                    return True

        if status == ApprovalStatus.REJECTED:
            if entity.report_id:
                report = await self._repos.reports.get_by_id(entity.report_id)
                if report is not None:
                    metadata = dict(report.report_metadata or {})
                    metadata["approval_status"] = ApprovalStatus.REJECTED.value
                    report.report_metadata = metadata
            if entity.executive_ranking_run_id:
                run = await self._repos.executive_rankings.get_by_id(
                    entity.executive_ranking_run_id
                )
                if run is not None:
                    metadata = dict(run.ranking_metadata or {})
                    metadata["approval_status"] = ApprovalStatus.REJECTED.value
                    run.ranking_metadata = metadata

        if status == ApprovalStatus.RESEARCH_REQUESTED:
            if entity.report_id:
                report = await self._repos.reports.get_by_id(entity.report_id)
                if report is not None:
                    metadata = dict(report.report_metadata or {})
                    metadata["approval_status"] = ApprovalStatus.RESEARCH_REQUESTED.value
                    report.report_metadata = metadata
            if entity.executive_ranking_run_id:
                run = await self._repos.executive_rankings.get_by_id(
                    entity.executive_ranking_run_id
                )
                if run is not None:
                    metadata = dict(run.ranking_metadata or {})
                    metadata["approval_status"] = ApprovalStatus.RESEARCH_REQUESTED.value
                    run.ranking_metadata = metadata
            await self._repos.approval_requests.append_audit_event(
                entity,
                {"event": "research_requested", "requires_follow_up": True},
            )

        await self._repos.session.flush()
        return False

    @staticmethod
    def _to_read(entity) -> ApprovalRequestRead:
        decisions = sorted(entity.decisions, key=lambda item: item.created_at)
        return ApprovalRequestRead(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            subject_type=ApprovalSubjectType(entity.subject_type),
            title=entity.title,
            status=ApprovalStatus(entity.status),
            executive_ranking_run_id=entity.executive_ranking_run_id,
            report_id=entity.report_id,
            audit_trail=entity.audit_trail or [],
            decisions=[ApprovalDecisionRead.model_validate(item) for item in decisions],
        )
