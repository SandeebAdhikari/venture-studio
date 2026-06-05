#!/usr/bin/env python3
"""Stripe Billing Corpus Validation: billing-focused collection + discovery validation."""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

from sqlalchemy import select, text
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
EXPERIMENT_CONFIG = API_ROOT / "config/collection_experiments/stripe_billing_corpus.json"
DOCS = ROOT / "docs"

B2B_DOMAINS = frozenset({"saas_b2b", "devtools", "ops_it", "fintech"})
B2B_PERSONAS = frozenset({"developer", "founder", "ops_admin", "product_manager", "marketer"})
VOCAB_TERMS = (
    "stripe",
    "billing",
    "subscription",
    "invoice",
    "chargeback",
    "payout",
    "webhook",
    "payment",
)

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


def _stage_value(stage) -> str:
    return stage.value if hasattr(stage, "value") else str(stage)


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return unescape(re.sub(r"<[^>]+>", " ", text)).strip()


def is_lane_relevant_complaint(
    *,
    title: str,
    summary: str,
    verbatim: str,
    domain: str,
    persona: str,
) -> bool:
    combined = f"{title} {summary} {verbatim}".lower()
    if "stripe" not in combined and "billing" not in combined and "subscription" not in combined:
        return False
    off_lane = (
        "facebook",
        "etsy",
        "hiring",
        "recruiting",
        "cofounder",
        "co-founder",
        "school",
        "music streaming",
        "spotify",
        "media client",
    )
    if any(term in combined for term in off_lane):
        return False
    founderish = persona in B2B_PERSONAS or domain in B2B_DOMAINS
    billing_context = any(
        term in combined
        for term in (
            "stripe",
            "billing",
            "subscription",
            "invoice",
            "chargeback",
            "payout",
            "webhook",
            "payment processing",
            "payment gateway",
            "merchant",
            "saas",
        )
    )
    return founderish and billing_context


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
        "experiment_name": payload["experiment"],
        "source_name": payload["source_name"],
        "previous_config": previous_config,
        "experiment_config": payload["config"],
    }


async def full_pattern_breakdown(repos, settings) -> dict:
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

    def pack_detailed(patterns):
        return [
            {
                "pattern_source": p.pattern_source,
                "topic": p.topic,
                "anchor": p.anchor_phrase,
                "complaint_count": p.complaint_count,
                "dominant_domain": p.domain_code,
                "dominant_persona": p.dominant_persona_code,
            }
            for p in patterns
        ]

    all_patterns = phrase + token + fallback
    return {
        "phrase_clustering": len(phrase),
        "token_clustering": len(token),
        "taxonomy_fallback": len(fallback),
        "total_patterns": len(all_patterns),
        "min_cluster_size": min_cluster,
        "patterns_detail": {
            "phrase_clustering": pack_detailed(phrase),
            "token_clustering": pack_detailed(token),
            "taxonomy_fallback": pack_detailed(fallback),
        },
    }


def measure_vocab(texts: list[str]) -> dict[str, int]:
    combined = " ".join(texts).lower()
    return {term: combined.count(term) for term in VOCAB_TERMS}


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
        collect_result = await ComplaintCollectionService(repos).collect_enabled_sources()
        await session.commit()

    started = datetime.now(UTC)
    async with factory() as session:
        repos = get_repositories(session)
        preflight = await DiscoveryValidationPreflight(repos).check()
        if not preflight.passed:
            print(json.dumps({"preflight_failed": list(preflight.errors)}, indent=2))
            return 1
        orchestrator = PipelineOrchestrator(repos, ServiceContainer(repos), settings)
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
        signals = list((await session.execute(select(Signal))).scalars().all())
        status = Counter(
            s.processing_status.value if hasattr(s.processing_status, "value") else str(s.processing_status)
            for s in signals
        )
        not_a_complaint = sum(1 for s in signals if s.skip_reason == "not_a_complaint")
        grounding = sum(
            1 for s in signals if s.skip_reason and "verbatim_quote" in s.skip_reason
        )

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
                )
            ).scalars().all()
        )

        lane_relevant = []
        for row in rows:
            title = _clean(row.signal.title if row.signal else "")
            summary = _clean(row.summary)
            verbatim = _clean(row.verbatim_quote)
            if is_lane_relevant_complaint(
                title=title,
                summary=summary,
                verbatim=verbatim,
                domain=row.domain.code,
                persona=row.persona.code,
            ):
                lane_relevant.append(
                    {
                        "thread_title": title[:120],
                        "domain": row.domain.code,
                        "category": row.category.code,
                        "persona": row.persona.code,
                        "severity": row.severity,
                        "summary": summary[:200],
                        "verbatim_excerpt": verbatim[:200],
                    }
                )

        signal_texts = [
            _clean(f"{s.title or ''} {s.body or ''}") for s in signals
        ]
        complaint_texts = [
            _clean(f"{r.summary} {r.verbatim_quote or ''}") for r in rows
        ]
        lane_texts = [
            _clean(f"{c['summary']} {c['verbatim_excerpt']}") for c in lane_relevant
        ]

        pattern_stats = await full_pattern_breakdown(get_repositories(session), settings)
        opps = list((await session.execute(select(Opportunity))).scalars().all())
        loaded = await get_repositories(session).pipelines.get_by_id_with_stages(
            pipeline_result.pipeline_run_id
        )
        gen_meta = {}
        if loaded:
            gen_stage = next(
                (s for s in loaded.stage_runs if _stage_value(s.stage) == "generate_opportunities"),
                None,
            )
            if gen_stage and gen_stage.stage_metadata:
                gen_meta = dict(gen_stage.stage_metadata)

        signals_n = len(signals)
        complaints_n = len(rows)
        lane_n = len(lane_relevant)
        precision = round(100 * lane_n / complaints_n, 1) if complaints_n else 0.0
        yield_pct = round(100 * complaints_n / signals_n, 1) if signals_n else 0.0

    verify = subprocess.run(
        [
            sys.executable,
            str(API_ROOT / "scripts/verify_discovery_validation.py"),
            "--pipeline-run-id",
            str(pipeline_result.pipeline_run_id),
            "--output",
            str(DOCS / "discovery-validation-verify-stripe-billing-corpus-2026-06-05.json"),
        ],
        cwd=str(API_ROOT),
        capture_output=True,
        text=True,
    )
    verify_json = json.loads(verify.stdout) if verify.stdout.strip() else {"stderr": verify.stderr}

    out = {
        "captured_at": finished.isoformat(),
        "label": "stripe-billing-corpus-validation",
        "experiment_name": "Stripe Billing Corpus Validation",
        "query_selection": {
            "selected_query": "Ask HN Stripe billing",
            "rationale": (
                "Highest recurring billing vocabulary (stripe/billing/subscription/invoice/webhook) "
                "among candidate pools at 90-signal collector cap; 113 Algolia nbHits; "
                "47 Ask HN threads with Stripe/billing in title in probe."
            ),
            "candidates_considered": [
                "Ask HN Stripe billing",
                "Ask HN Stripe alternative",
                "Ask HN Alternatives to Stripe",
                "Ask HN Stripe subscription",
                "Ask HN Stripe chargeback",
                "Ask HN Stripe payment processing",
            ],
        },
        "config_change": config_change,
        "collection": {
            "sources_processed": collect_result.sources_processed,
            "inserted": collect_result.inserted,
        },
        "collection_metrics": {
            "signals_collected": signals_n,
            "complaints_extracted": complaints_n,
            "lane_relevant_complaints": lane_n,
            "complaint_precision_pct": precision,
            "complaint_yield_pct": yield_pct,
            "not_a_complaint_count": not_a_complaint,
            "grounding_failure_count": grounding,
            "signal_processing_status": dict(status),
        },
        "recurring_vocabulary": {
            "signals": measure_vocab(signal_texts),
            "all_complaints": measure_vocab(complaint_texts),
            "lane_relevant_complaints": measure_vocab(lane_texts),
        },
        "top_lane_relevant_complaints": lane_relevant[:20],
        "pattern_discovery": {
            "phrase_patterns": pattern_stats["phrase_clustering"],
            "token_patterns": pattern_stats["token_clustering"],
            "fallback_patterns": pattern_stats["taxonomy_fallback"],
            "total_patterns": pattern_stats["total_patterns"],
            "min_cluster_size": pattern_stats["min_cluster_size"],
            "patterns": pattern_stats["patterns_detail"],
        },
        "opportunity_results": {
            "opportunities_generated": len(opps),
            "opportunity_titles": [o.title for o in opps],
            "generate_stage_metadata": gen_meta,
        },
        "pipeline": {
            "pipeline_run_id": str(pipeline_result.pipeline_run_id),
            "status": pipeline_result.status.value,
            "stages_completed": pipeline_result.stages_completed,
            "duration_seconds": (finished - started).total_seconds(),
        },
        "verify": verify_json,
    }

    output_path = DOCS / "discovery-validation-run-stripe-billing-corpus-2026-06-05.json"
    output_path.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2))
    await close_db()
    return 0 if verify.returncode == 0 else verify.returncode


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
