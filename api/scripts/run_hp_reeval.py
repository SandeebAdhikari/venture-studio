#!/usr/bin/env python3
"""HP-REEVAL-1: Re-run Human Proxy for legacy current evaluations."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.human_proxy.service import HumanProxyService
from app.config import get_settings
from app.db.session import close_db, get_session_factory, init_db
from app.repositories import get_repositories


async def main() -> None:
    parser = argparse.ArgumentParser(description="Re-evaluate legacy human proxy evaluations")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List targets without invoking the LLM",
    )
    parser.add_argument(
        "--all-scale-versions",
        action="store_true",
        help="Re-evaluate all current evaluations, not only scale_version=legacy",
    )
    args = parser.parse_args()

    init_db()
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        repos = get_repositories(session)
        service = HumanProxyService(repos, settings)
        result = await service.reevaluate_current(
            legacy_only=not args.all_scale_versions,
            dry_run=args.dry_run,
        )
        await session.commit()
        print(
            json.dumps(
                {
                    "dry_run": result.dry_run,
                    "profiles_processed": result.profiles_processed,
                    "targets_identified": result.targets_identified,
                    "skipped_century_v1": result.skipped_century_v1,
                    "completed": result.completed,
                    "skipped": result.skipped,
                    "failed": result.failed,
                    "items": [
                        {
                            "opportunity_id": str(item.opportunity_id),
                            "founder_profile_id": str(item.founder_profile_id),
                            "status": item.status,
                            "skip_reason": item.skip_reason,
                            "error": item.error,
                            "human_proxy_evaluation_id": (
                                str(item.human_proxy_evaluation_id)
                                if item.human_proxy_evaluation_id
                                else None
                            ),
                        }
                        for item in result.items
                    ],
                },
                indent=2,
            )
        )
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
