#!/usr/bin/env python3
"""EXEC-RANK-REGEN-1: Regenerate executive rankings after HP-REEVAL-1."""

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


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate current executive ranking with century_v1 founder-fit semantics"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview targets without creating a new ranking run",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Number of top opportunities to highlight (defaults to settings)",
    )
    args = parser.parse_args()

    init_db()
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        repos = get_repositories(session)
        service = ExecutiveRankingService(repos, settings)
        result = await service.regenerate_current_rankings(
            top_n=args.top_n,
            dry_run=args.dry_run,
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
                    "opportunity_count": result.opportunity_count,
                    "rankable_opportunity_count": result.rankable_opportunity_count,
                    "century_v1_hp_count": result.century_v1_hp_count,
                    "stale_entry_count": result.stale_entry_count,
                    "superseded_run_id": (
                        str(result.superseded_run_id) if result.superseded_run_id else None
                    ),
                    "superseded_version": result.superseded_version,
                    "ranking_run_id": (
                        str(result.ranking_run_id) if result.ranking_run_id else None
                    ),
                    "version": result.version,
                    "ranked_opportunity_count": result.ranked_opportunity_count,
                    "top_opportunities": [
                        {
                            "opportunity_id": str(item.opportunity_id),
                            "opportunity_title": item.opportunity_title,
                            "rank": item.rank,
                            "final_opportunity_score": item.final_opportunity_score,
                            "founder_fit_score": item.founder_fit_score,
                            "ranking_details": item.ranking_details,
                        }
                        for item in result.top_opportunities
                    ],
                },
                indent=2,
            )
        )
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
