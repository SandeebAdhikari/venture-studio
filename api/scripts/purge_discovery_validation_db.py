#!/usr/bin/env python3
"""Purge mock/E2E and stale discovery artifacts for a clean validation run.

Keeps: taxonomy, sources, founder profiles, migrations metadata.
Removes: signals through venture reports (discovery chain).
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.db.session import close_db, get_session_factory, init_db

PURGE_SQL = """
DELETE FROM approval_decisions;
DELETE FROM approval_requests;
DELETE FROM executive_ranking_entries;
DELETE FROM executive_ranking_runs;
DELETE FROM reports;
DELETE FROM human_proxy_evaluations;
DELETE FROM growth_evaluations;
DELETE FROM gtm_plans;
DELETE FROM product_strategies;
DELETE FROM revenue_validations;
DELETE FROM customer_research;
DELETE FROM competitor_analyses;
DELETE FROM market_briefs;
DELETE FROM opportunity_scores;
DELETE FROM opportunity_complaints;
DELETE FROM opportunities;
DELETE FROM complaints;
DELETE FROM signals;
"""


async def main() -> int:
    init_db()
    factory = get_session_factory()
    async with factory() as session:
        for stmt in PURGE_SQL.strip().split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            result = await session.execute(text(stmt))
            print(f"{stmt.split()[2]}: {result.rowcount} rows")
        await session.commit()

        checks = [
            ("opportunities", "SELECT count(*)::int FROM opportunities"),
            ("mock_opps", "SELECT count(*)::int FROM opportunities WHERE llm_model LIKE 'mock-%'"),
            ("complaints", "SELECT count(*)::int FROM complaints"),
            ("signals", "SELECT count(*)::int FROM signals"),
            ("ranking_runs", "SELECT count(*)::int FROM executive_ranking_runs"),
            ("venture_reports", "SELECT count(*)::int FROM reports"),
        ]
        print("--- after purge ---")
        for name, q in checks:
            n = (await session.execute(text(q))).scalar_one()
            print(f"{name}: {n}")
    await close_db()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
