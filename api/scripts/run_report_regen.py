#!/usr/bin/env python3
"""VENTURE-REPORT-REGEN-1: Regenerate venture reports from current ranking and HP."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.db.session import close_db, get_session_factory, init_db
from app.ranking.service import ExecutiveRankingService
from app.repositories import get_repositories
from app.reports.venture.service import VentureReportService


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate venture recommendation report from current ranking and agents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview regeneration without creating a new report",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Number of top opportunities to include (defaults to settings)",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Create report as draft instead of published",
    )
    args = parser.parse_args()

    init_db()
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        repos = get_repositories(session)
        ranking_service = ExecutiveRankingService(repos, settings)
        venture_service = VentureReportService(
            repos,
            settings,
            ranking_service=ranking_service,
        )
        result = await venture_service.regenerate_current_reports(
            top_n=args.top_n,
            dry_run=args.dry_run,
            publish=not args.no_publish,
        )
        if not args.dry_run:
            await session.commit()
        print(
            json.dumps(
                {
                    "dry_run": result.dry_run,
                    "founder_profile_id": (
                        str(result.founder_profile_id) if result.founder_profile_id else None
                    ),
                    "top_n": result.top_n,
                    "opportunities_found": result.opportunities_found,
                    "current_reports_found": result.current_reports_found,
                    "stale_reports_found": result.stale_reports_found,
                    "current_ranking_run_id": (
                        str(result.current_ranking_run_id)
                        if result.current_ranking_run_id
                        else None
                    ),
                    "current_ranking_version": result.current_ranking_version,
                    "century_v1_hp_count": result.century_v1_hp_count,
                    "superseded_report_id": (
                        str(result.superseded_report_id)
                        if result.superseded_report_id
                        else None
                    ),
                    "report_id": str(result.report_id) if result.report_id else None,
                    "title": result.title,
                    "summary": result.summary,
                    "opportunity_count": result.opportunity_count,
                },
                indent=2,
            )
        )
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
