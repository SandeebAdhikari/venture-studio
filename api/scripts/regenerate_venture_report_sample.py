#!/usr/bin/env python3
"""Regenerate venture report markdown for the latest ranked opportunity (quality check)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.db.session import close_db, get_session_factory, init_db
from app.repositories import get_repositories
from app.reports.venture.service import VentureReportService
from app.ranking.service import ExecutiveRankingService


async def main() -> None:
    init_db()
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        repos = get_repositories(session)
        ranking_service = ExecutiveRankingService(repos, settings)
        try:
            current = await ranking_service.get_current_ranking()
        except Exception as exc:
            print(json.dumps({"error": str(exc)}))
            return

        venture_service = VentureReportService(repos, settings)
        result = await venture_service.generate_venture_report(
            ranking_run_id=current.id,
            founder_profile_id=current.founder_profile_id,
            generate_ranking_if_missing=False,
            publish=False,
        )

        report = await repos.reports.get_by_id(result.report_id)
        payload = {
            "report_id": str(result.report_id),
            "ranking_run_id": str(current.id),
            "markdown_length": len(result.markdown),
            "has_raw_dict": "{" in result.markdown and "'phase_name'" in result.markdown,
            "founder_fit_lines": [
                line
                for line in result.markdown.splitlines()
                if "Founder fit" in line or "founder fit" in line.lower()
            ][:6],
            "market_disclaimer": "unaudited model estimates" in result.markdown.lower()
            or "supporting evidence" in result.markdown.lower(),
            "sample_roadmap": next(
                (
                    line
                    for line in result.markdown.splitlines()
                    if "Phase" in line and "weeks" in line
                ),
                None,
            ),
            "markdown_excerpt": result.markdown[:2500],
        }
        if report:
            payload["report_metadata"] = report.report_metadata
        print(json.dumps(payload, indent=2))
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
