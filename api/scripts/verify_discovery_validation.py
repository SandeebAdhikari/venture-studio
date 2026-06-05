#!/usr/bin/env python3
"""Post-run verification for real venture discovery validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from app.db.session import close_db, get_session_factory, init_db

MOCK_TABLES = [
    ("opportunities", "llm_model"),
    ("market_briefs", "llm_model"),
    ("competitor_analyses", "llm_model"),
    ("customer_research", "llm_model"),
    ("revenue_validations", "llm_model"),
    ("product_strategies", "llm_model"),
    ("gtm_plans", "llm_model"),
    ("growth_evaluations", "llm_model"),
    ("human_proxy_evaluations", "llm_model"),
]


async def verify(pipeline_run_id: UUID | None) -> dict:
    init_db()
    factory = get_session_factory()
    out: dict = {"passed": True, "checks": [], "errors": []}

    async with factory() as session:
        for table, col in MOCK_TABLES:
            q = text(
                f"SELECT count(*)::int FROM {table} WHERE {col} LIKE 'mock-%'"  # noqa: S608
            )
            n = (await session.execute(q)).scalar_one()
            ok = n == 0
            out["checks"].append({"name": f"no_mock_{table}", "ok": ok, "count": n})
            if not ok:
                out["passed"] = False
                out["errors"].append(f"{table} has {n} mock-* rows")

        e2e = (
            await session.execute(
                text(
                    "SELECT count(*)::int FROM opportunities "
                    "WHERE title ILIKE '%E2E%' OR llm_model LIKE 'mock-%'"
                )
            )
        ).scalar_one()
        ok = e2e == 0
        out["checks"].append({"name": "no_e2e_opportunities", "ok": ok, "count": e2e})
        if not ok:
            out["passed"] = False
            out["errors"].append(f"E2E/mock opportunities: {e2e}")

        new_complaints = (
            await session.execute(text("SELECT count(*)::int FROM complaints"))
        ).scalar_one()
        new_opps = (
            await session.execute(text("SELECT count(*)::int FROM opportunities"))
        ).scalar_one()
        new_briefs = (
            await session.execute(
                text(
                    "SELECT count(*)::int FROM market_briefs "
                    "WHERE is_current AND status = 'completed'"
                )
            )
        ).scalar_one()
        ranking = (
            await session.execute(
                text(
                    "SELECT id, created_at, ranking_metadata "
                    "FROM executive_ranking_runs "
                    "WHERE is_current ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).first()
        report = (
            await session.execute(
                text(
                    "SELECT id, title, created_at, metadata AS report_metadata "
                    "FROM reports "
                    "WHERE report_type = 'venture_recommendation' "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).first()

        out["artifacts"] = {
            "complaints": new_complaints,
            "opportunities": new_opps,
            "completed_market_briefs": new_briefs,
            "current_ranking": dict(ranking._mapping) if ranking else None,
            "latest_venture_report": dict(report._mapping) if report else None,
        }

        report_metadata = {}
        if report is not None:
            meta_row = (
                await session.execute(
                    text(
                        "SELECT metadata FROM reports WHERE id = :id"
                    ),
                    {"id": str(report._mapping["id"])},
                )
            ).first()
            if meta_row is not None:
                report_metadata = meta_row._mapping.get("metadata") or {}

        empty_discovery = (
            new_opps == 0
            and report is not None
            and (
                report_metadata.get("outcome") == "empty_discovery"
                or (report_metadata.get("opportunity_count") == 0)
            )
        )
        out["empty_discovery"] = empty_discovery

        ok = new_complaints >= 1
        out["checks"].append({"name": "fresh_complaints", "ok": ok, "count": new_complaints})
        if not ok:
            out["passed"] = False
            out["errors"].append(f"Expected complaints >= 1, got {new_complaints}")

        if empty_discovery:
            ok = new_opps == 0
            out["checks"].append(
                {"name": "empty_discovery_opportunities", "ok": ok, "count": new_opps}
            )
            if not ok:
                out["passed"] = False
                out["errors"].append(
                    f"Empty discovery run expected 0 opportunities, got {new_opps}"
                )
        else:
            for key, min_val in [
                ("opportunities", 1),
                ("completed_market_briefs", 1),
            ]:
                val = out["artifacts"][key]
                ok = val >= min_val
                out["checks"].append({"name": f"fresh_{key}", "ok": ok, "count": val})
                if not ok:
                    out["passed"] = False
                    out["errors"].append(f"Expected {key} >= {min_val}, got {val}")

        ok = ranking is not None
        out["checks"].append({"name": "fresh_ranking", "ok": ok})
        if not ok:
            out["passed"] = False
            out["errors"].append("No current executive ranking")

        ok = report is not None
        out["checks"].append({"name": "fresh_venture_report", "ok": ok})
        if not ok:
            out["passed"] = False
            out["errors"].append("No venture recommendation report")

        if pipeline_run_id:
            run = (
                await session.execute(
                    text(
                        "SELECT status, started_at, finished_at, config_snapshot "
                        "FROM pipeline_runs WHERE id = :id"
                    ),
                    {"id": str(pipeline_run_id)},
                )
            ).first()
            out["pipeline_run"] = dict(run._mapping) if run else None
            if run is not None and empty_discovery:
                status_ok = run._mapping.get("status") == "completed"
                out["checks"].append(
                    {
                        "name": "empty_discovery_pipeline_completed",
                        "ok": status_ok,
                        "status": run._mapping.get("status"),
                    }
                )
                if not status_ok:
                    out["passed"] = False
                    out["errors"].append(
                        "Empty discovery run must finish with pipeline status completed"
                    )

        top = (
            await session.execute(
                text(
                    """
                    SELECT o.title, o.llm_model, e.rank, e.final_opportunity_score
                    FROM executive_ranking_entries e
                    JOIN executive_ranking_runs r ON r.id = e.executive_ranking_run_id AND r.is_current
                    JOIN opportunities o ON o.id = e.opportunity_id
                    ORDER BY e.rank ASC
                    LIMIT 3
                    """
                )
            )
        ).fetchall()
        out["top_ranked"] = [dict(r._mapping) for r in top]

        models = (
            await session.execute(
                text(
                    """
                    SELECT DISTINCT llm_model FROM market_briefs WHERE is_current
                    UNION SELECT DISTINCT llm_model FROM opportunities
                    """
                )
            )
        ).fetchall()
        out["llm_models_seen"] = [r[0] for r in models]

    await close_db()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-run-id", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    run_id = UUID(args.pipeline_run_id) if args.pipeline_run_id else None
    result = asyncio.run(verify(run_id))
    text_out = json.dumps(result, indent=2, default=str)
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(text_out)
    print(text_out)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
