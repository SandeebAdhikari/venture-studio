#!/usr/bin/env python3
"""Validate founder-signal opportunity persistence after validation alignment."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.agents.opportunity.founder_signal_clustering import detect_founder_signal_patterns
from app.agents.opportunity.patterns import TopicPatternDetector, detect_token_clustering_patterns
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import detect_taxonomy_fallback_patterns, resolve_generation_patterns
from app.config import get_settings
from app.db.models.complaint import Complaint
from app.db.models.opportunity import Opportunity
from app.db.session import close_db, get_session_factory, init_db
from app.repositories import get_repositories
from app.agents.opportunity.service import OpportunityGeneratorService

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parents[1]
SIGNALS_CONFIG = API_ROOT / "config/collection_experiments/stripe_billing_founder_signals.json"
DOCS = ROOT / "docs"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _to_evidence(complaint: Complaint, signal_overrides: dict) -> ComplaintEvidence:
    override = signal_overrides.get(str(complaint.id), {})
    return ComplaintEvidence(
        id=complaint.id,
        summary=complaint.summary,
        verbatim_quote=complaint.verbatim_quote,
        severity=complaint.severity,
        domain_code=complaint.domain.code,
        category_code=complaint.category.code,
        persona_code=complaint.persona.code,
        product_mentions=list(complaint.product_mentions or []),
        business_function_code=override.get("business_function_code")
        or complaint.business_function_code,
        jtbd_code=override.get("jtbd_code") or complaint.jtbd_code,
        consequence_code=override.get("consequence_code") or complaint.consequence_code,
    )


async def main() -> int:
    signals_doc = _load_json(SIGNALS_CONFIG)
    signal_overrides = signals_doc["complaint_signals"]
    lane_ids = set(signal_overrides.keys())

    init_db()
    factory = get_session_factory()
    async with factory() as session:
        before_opportunities = await session.scalar(select(func.count()).select_from(Opportunity))
        complaints = (
            (
                await session.execute(
                    select(Complaint)
                    .options(
                        selectinload(Complaint.category),
                        selectinload(Complaint.domain),
                        selectinload(Complaint.persona),
                    )
                    .order_by(Complaint.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        repos = get_repositories(session)
        settings = get_settings()
        service = OpportunityGeneratorService(repos, settings)

        lane_complaints = [c for c in complaints if str(c.id) in lane_ids]
        evidence = [_to_evidence(c, signal_overrides) for c in lane_complaints]
        evidence_by_id = {item.id: item for item in evidence}

        phrase_patterns = TopicPatternDetector().detect(
            evidence,
            min_cluster_size=settings.min_cluster_size,
        )
        token_patterns = detect_token_clustering_patterns(
            evidence,
            min_cluster_size=settings.min_cluster_size,
        )
        founder_patterns = detect_founder_signal_patterns(
            evidence,
            min_cluster_size=settings.min_cluster_size,
            variant="B",
        )
        fallback_patterns = detect_taxonomy_fallback_patterns(evidence)
        resolved_patterns = resolve_generation_patterns(evidence, phrase_patterns)

        generation_results = []
        for pattern in founder_patterns:
            pattern_evidence = [
                evidence_by_id[complaint_id]
                for complaint_id in pattern.complaint_ids
                if complaint_id in evidence_by_id
            ]
            item = await service.generate_for_pattern(pattern, pattern_evidence)
            generation_results.append(
                {
                    "cluster_key": pattern.anchor_phrase,
                    "topic": pattern.topic,
                    "pattern_source": pattern.pattern_source,
                    "complaint_count": pattern.complaint_count,
                    "status": item.status,
                    "skip_reason": item.skip_reason,
                    "error": item.error,
                    "opportunity_id": str(item.opportunity_id) if item.opportunity_id else None,
                    "draft_title": item.draft.title if item.draft else None,
                }
            )

        await session.commit()
        after_opportunities = await session.scalar(select(func.count()).select_from(Opportunity))

    await close_db()

    report = {
        "experiment": "founder_signal_opportunity_persistence_validation",
        "generated_at": datetime.now(UTC).isoformat(),
        "lane_relevant_complaints": len(lane_complaints),
        "patterns": {
            "phrase": len(phrase_patterns),
            "token": len(token_patterns),
            "founder_signal": len(founder_patterns),
            "taxonomy_fallback_direct": len(fallback_patterns),
            "resolved_for_generation": len(resolved_patterns),
            "founder_signal_details": [
                {
                    "cluster_key": p.anchor_phrase,
                    "topic": p.topic,
                    "complaint_count": p.complaint_count,
                    "complaint_ids": [str(cid) for cid in p.complaint_ids],
                }
                for p in founder_patterns
            ],
        },
        "regression_checks": {
            "phrase_unchanged_zero": len(phrase_patterns) == 0,
            "token_unchanged_zero": len(token_patterns) == 0,
            "taxonomy_fallback_unchanged_zero": len(fallback_patterns) == 0,
        },
        "opportunities_before": before_opportunities,
        "opportunities_after": after_opportunities,
        "opportunities_created_this_run": (after_opportunities or 0) - (before_opportunities or 0),
        "generation_results": generation_results,
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    output_path = DOCS / "founder-signal-opportunity-persistence-validation-2026-06-05.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
