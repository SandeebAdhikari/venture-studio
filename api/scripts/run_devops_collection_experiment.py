#!/usr/bin/env python3
"""Apply DevOps collection experiment config, collect, run discovery validation, report results."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import selectinload

from app.agents.opportunity.patterns import TopicPatternDetector, detect_token_clustering_patterns
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import detect_taxonomy_fallback_patterns
from app.collectors.hn_algolia import register_hn_algolia_collector
from app.collection.service import ComplaintCollectionService
from app.config import get_settings
from app.db.models.complaint import Complaint
from app.db.models.opportunity import Opportunity
from app.db.models.signal import Signal
from app.db.session import close_db, get_session_factory, init_db
from app.discovery.validation import DiscoveryValidationPreflight
from app.pipeline.orchestrator import PipelineOrchestrator
from app.repositories import get_repositories
from app.schemas.pipeline import PipelineRunOptions
from app.schemas.source import SourceUpdate
from app.services.container import ServiceContainer

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_CONFIG = API_ROOT / "config/collection_experiments/devops_deployment.json"
DOCS = ROOT / "docs"

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


async def purge_discovery_chain(session) -> None:
    for stmt in PURGE_SQL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            await session.execute(text(stmt))


async def apply_experiment_config(session) -> dict:
    payload = json.loads(EXPERIMENT_CONFIG.read_text())
    repos = get_repositories(session)
    source = await repos.sources.get_by_name(payload["source_name"])
    if source is None:
        raise RuntimeError(f"Source not found: {payload['source_name']}")
    previous_config = dict(source.config or {})
    await repos.sources.update(source, SourceUpdate(config=payload["config"]))
    await session.commit()
    return {
        "source_name": payload["source_name"],
        "previous_config": previous_config,
        "experiment_config": payload["config"],
    }


async def pattern_breakdown(repos, settings) -> dict:
    complaints = await repos.complaints.list_unlinked_for_generation(
        window_days=settings.cluster_window_days,
        limit=settings.generation_batch_size,
    )
    evidence = [
        ComplaintEvidence(
            id=c.id,
            summary=c.summary,
            verbatim_quote=c.verbatim_quote,
            severity=c.severity,
            domain_code=c.domain.code,
            category_code=c.category.code,
            persona_code=c.persona.code,
            product_mentions=list(c.product_mentions or []),
        )
        for c in complaints
    ]
    min_cluster = settings.min_cluster_size
    phrase = TopicPatternDetector().detect(evidence, min_cluster_size=min_cluster)
    token = detect_token_clustering_patterns(evidence, min_cluster_size=min_cluster)
    fallback = detect_taxonomy_fallback_patterns(evidence)

    def pack(patterns):
        return [
            {
                "topic": p.topic,
                "anchor_phrase": p.anchor_phrase,
                "complaint_count": p.complaint_count,
                "pattern_source": p.pattern_source,
            }
            for p in patterns
        ]

    return {
        "complaints_unlinked": len(evidence),
        "phrase_clustering": len(phrase),
        "token_clustering": len(token),
        "taxonomy_fallback": len(fallback),
        "patterns": {
            "phrase_clustering": pack(phrase),
            "token_clustering": pack(token),
            "taxonomy_fallback": pack(fallback),
        },
    }


async def main() -> int:
    settings = get_settings()
    register_hn_algolia_collector()
    init_db()
    factory = get_session_factory()

    async with factory() as session:
        config_change = await apply_experiment_config(session)

    async with factory() as session:
        await purge_discovery_chain(session)
        await session.commit()

    async with factory() as session:
        repos = get_repositories(session)
        collection = ComplaintCollectionService(repos)
        collect_result = await collection.collect_enabled_sources()
        await session.commit()

    started = datetime.now(UTC)
    async with factory() as session:
        repos = get_repositories(session)
        preflight = await DiscoveryValidationPreflight(repos).check()
        if not preflight.passed:
            print(json.dumps({"preflight_failed": list(preflight.errors)}, indent=2))
            return 1
        services = ServiceContainer(repos)
        orchestrator = PipelineOrchestrator(repos, services, settings)
        pipeline_result = await orchestrator.run_pipeline(
            options=PipelineRunOptions(
                discovery_validation_mode=True,
                force=True,
                stop_on_failure=True,
            )
        )
        await session.commit()
    finished = datetime.now(UTC)

    async with factory() as session:
        repos = get_repositories(session)
        signals = int((await session.execute(select(func.count()).select_from(Signal))).scalar_one())
        complaints = int((await session.execute(select(func.count()).select_from(Complaint))).scalar_one())
        opportunities = int((await session.execute(select(func.count()).select_from(Opportunity))).scalar_one())
        pattern_stats = await pattern_breakdown(repos, settings)

        rows = list(
            (
                await session.execute(
                    select(Complaint)
                    .options(
                        selectinload(Complaint.category),
                        selectinload(Complaint.domain),
                        selectinload(Complaint.persona),
                        selectinload(Complaint.signal),
                    )
                    .order_by(Complaint.created_at)
                    .limit(12)
                )
            ).scalars().all()
        )
        sample_complaints = [
            {
                "summary": row.summary[:120],
                "verbatim": (row.verbatim_quote or "")[:120],
                "domain": row.domain.code,
                "category": row.category.code,
                "persona": row.persona.code,
                "severity": row.severity,
                "signal_title": (row.signal.title if row.signal else "")[:80],
            }
            for row in rows
        ]

        gen_stage = None
        loaded = await repos.pipelines.get_by_id_with_stages(pipeline_result.pipeline_run_id)
        if loaded:
            gen_stage = next(
                (
                    s
                    for s in loaded.stage_runs
                    if (s.stage.value if hasattr(s.stage, "value") else s.stage)
                    == "generate_opportunities"
                ),
                None,
            )

    verify = subprocess.run(
        [
            sys.executable,
            str(API_ROOT / "scripts/verify_discovery_validation.py"),
            "--pipeline-run-id",
            str(pipeline_result.pipeline_run_id),
            "--output",
            str(DOCS / "discovery-validation-verify-devops-experiment-2026-06-05.json"),
        ],
        cwd=str(API_ROOT),
        capture_output=True,
        text=True,
    )
    verify_json = json.loads(verify.stdout) if verify.stdout.strip() else {"stderr": verify.stderr}

    out = {
        "captured_at": finished.isoformat(),
        "label": "devops-deployment-collection-experiment",
        "config_change": config_change,
        "collection": {
            "sources_processed": collect_result.sources_processed,
            "inserted": collect_result.inserted,
            "duplicates": collect_result.duplicates,
            "skipped": collect_result.skipped,
        },
        "signals_collected": signals,
        "complaints_extracted": complaints,
        "phrase_patterns": pattern_stats["phrase_clustering"],
        "token_patterns": pattern_stats["token_clustering"],
        "fallback_patterns": pattern_stats["taxonomy_fallback"],
        "opportunities_generated": opportunities,
        "sample_patterns": pattern_stats["patterns"],
        "sample_complaints": sample_complaints,
        "pipeline": {
            "pipeline_run_id": str(pipeline_result.pipeline_run_id),
            "status": pipeline_result.status.value,
            "stages_completed": pipeline_result.stages_completed,
            "stages_failed": pipeline_result.stages_failed,
            "duration_seconds": (finished - started).total_seconds(),
            "generate_opportunities": {
                "items_in": gen_stage.items_in if gen_stage else None,
                "items_out": gen_stage.items_out if gen_stage else None,
            },
        },
        "verify": verify_json,
    }

    output_path = DOCS / "discovery-validation-run-devops-experiment-2026-06-05.json"
    output_path.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2))
    await close_db()
    return 0 if verify.returncode == 0 else verify.returncode


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
