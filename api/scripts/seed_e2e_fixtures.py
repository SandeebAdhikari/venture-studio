#!/usr/bin/env python3
"""Seed deterministic DB state for Playwright E2E (approvals, reports, pipeline).

Run after migrations with REQUIRE_FOUNDER_APPROVAL=true, e.g.:

  cd api && PYTHONPATH=. REQUIRE_FOUNDER_APPROVAL=true python scripts/seed_e2e_fixtures.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.config import get_settings
from app.db.enums import (
    PipelineRunStatus,
    PipelineStage,
    PipelineStageStatus,
    PipelineTrigger,
)
from app.db.models.category import Category
from app.db.enums import CategoryKind
from app.db.session import close_db, get_session_factory, init_db
from app.ranking.service import ExecutiveRankingService
from app.reports.venture.service import VentureReportService
from app.repositories import get_repositories
from app.schemas.pipeline import PipelineRunCreate, PipelineStageRunCreate
from app.services.approval import ApprovalService
from tests.ranking.test_executive_ranking_service import (
    AgentScoreProfile,
    _create_opportunity,
    _seed_agent_outputs,
)

E2E_MARKER = "e2e_playwright_seed_v1"


async def _taxonomy_ids(session) -> tuple:
    category = await session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    if category is None or domain is None or persona is None:
        raise RuntimeError("Missing seeded taxonomy categories; run Alembic migrations first.")
    return category.id, domain.id, persona.id


async def seed() -> dict[str, str]:
    settings = get_settings()
    if not settings.require_founder_approval:
        raise RuntimeError("REQUIRE_FOUNDER_APPROVAL must be true for E2E approval tests.")

    session_factory = get_session_factory()
    async with session_factory() as session:
        repos = get_repositories(session)
        existing = await repos.pipelines.list_runs(limit=5)
        for run in existing:
            snapshot = run.config_snapshot or {}
            if snapshot.get("e2e_marker") == E2E_MARKER:
                return {"status": "already_seeded", "marker": E2E_MARKER}

        taxonomy = await _taxonomy_ids(session)
        profile = await repos.founder_profiles.get_default()
        if profile is None:
            raise RuntimeError("No default founder profile")

        approval = ApprovalService(repos, settings)
        ranking_service = ExecutiveRankingService(repos, settings, approval_service=approval)
        venture_service = VentureReportService(
            repos,
            settings,
            ranking_service=ranking_service,
            approval_service=approval,
        )

        opportunity = await _create_opportunity(
            session,
            taxonomy,
            title="E2E Approval Workflow SaaS",
        )
        await _seed_agent_outputs(
            repos,
            opportunity.id,
            profile.id,
            AgentScoreProfile(),
        )
        await session.commit()

        ranking = await ranking_service.generate_ranking(top_n=3)
        report_a = await venture_service.generate_venture_report(
            top_n=3,
            generate_ranking_if_missing=False,
        )
        ranking_b = await ranking_service.generate_ranking(top_n=3)
        report_b = await venture_service.generate_venture_report(
            top_n=3,
            ranking_run_id=ranking_b.ranking_run_id,
            generate_ranking_if_missing=False,
        )

        pipeline_run = await repos.pipelines.create_run(
            PipelineRunCreate(
                trigger=PipelineTrigger.SCHEDULED,
                config_snapshot={"e2e_marker": E2E_MARKER, "note": "Playwright visibility fixture"},
            )
        )
        await repos.pipelines.create_stage_runs(
            pipeline_run.id,
            [
                PipelineStageRunCreate(
                    stage=PipelineStage.COLLECT,
                    sequence=1,
                    max_attempts=1,
                ),
                PipelineStageRunCreate(
                    stage=PipelineStage.VENTURE_REPORT,
                    sequence=14,
                    max_attempts=1,
                ),
            ],
        )
        await repos.pipelines.mark_run_started(pipeline_run)
        for stage in (PipelineStage.COLLECT, PipelineStage.VENTURE_REPORT):
            stage_run = await repos.pipelines.get_stage_run(pipeline_run.id, stage.value)
            if stage_run is None:
                continue
            await repos.pipelines.mark_stage_started(stage_run)
            await repos.pipelines.mark_stage_completed(
                stage_run,
                items_in=1,
                items_out=1,
                items_failed=0,
                records_processed=1,
            )
        await repos.pipelines.update_run_counters(
            pipeline_run,
            stages_completed=2,
            stages_failed=0,
            stages_skipped=0,
        )
        await repos.pipelines.mark_run_finished(
            pipeline_run,
            status=PipelineRunStatus.COMPLETED,
        )

        await session.commit()

        return {
            "status": "seeded",
            "marker": E2E_MARKER,
            "ranking_run_id": str(ranking.ranking_run_id),
            "venture_report_a": str(report_a.report_id),
            "venture_report_b": str(report_b.report_id),
            "pipeline_run_id": str(pipeline_run.id),
        }


async def main() -> int:
    os.environ.setdefault("REQUIRE_FOUNDER_APPROVAL", "true")
    get_settings.cache_clear()
    settings = get_settings()
    init_db(settings)
    try:
        result = await seed()
        for key, value in result.items():
            print(f"{key}={value}")
        return 0
    except Exception as exc:
        print(f"seed_e2e_fixtures failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await close_db()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
