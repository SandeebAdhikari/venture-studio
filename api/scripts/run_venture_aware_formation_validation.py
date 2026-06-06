#!/usr/bin/env python3
"""Validate venture-aware formation on the Stripe Billing corpus."""

from __future__ import annotations

import asyncio
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.classification.founder_signals import format_venture_cluster_key
from app.agents.opportunity.founder_signal_clustering import (
    detect_founder_signal_patterns,
    MIN_FOUNDER_CLUSTER_SIZE,
)
from app.agents.opportunity.mechanism_fingerprints import (
    enrich_complaint_evidence,
    evaluate_singleton_exception,
    extract_mechanism_fingerprint,
)
from app.agents.opportunity.patterns import TopicPatternDetector, detect_token_clustering_patterns
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import resolve_generation_patterns
from app.agents.opportunity.venture_aware_clustering import detect_venture_aware_patterns
from app.db.models.complaint import Complaint
from app.db.session import close_db, get_session_factory, init_db

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parents[1]
SIGNALS_CONFIG = API_ROOT / "config/collection_experiments/stripe_billing_founder_signals.json"
CORPUS_CONFIG = API_ROOT / "config/collection_experiments/stripe_billing_corpus.json"
DOCS = ROOT / "docs"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _to_evidence(complaint: Complaint, signal_overrides: dict) -> ComplaintEvidence:
    override = signal_overrides.get(str(complaint.id), {})
    return enrich_complaint_evidence(
        ComplaintEvidence(
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
    )


def _cluster_inventory(evidence: list[ComplaintEvidence]) -> list[dict]:
    enriched = [enrich_complaint_evidence(member) for member in evidence]
    keyed: dict[str, list[ComplaintEvidence]] = defaultdict(list)

    for member in enriched:
        if (
            member.business_function_code is None
            or member.jtbd_code is None
            or member.consequence_code is None
            or member.mechanism_fingerprint is None
        ):
            continue
        cluster_key = format_venture_cluster_key(
            business_function_code=member.business_function_code,
            jtbd_code=member.jtbd_code,
            consequence_code=member.consequence_code,
            mechanism_fingerprint=member.mechanism_fingerprint,
        )
        keyed[cluster_key].append(member)

    inventory: list[dict] = []
    for cluster_key, members in sorted(keyed.items(), key=lambda item: (-len(item[1]), item[0])):
        cluster_size = len(members)
        singleton_reason = None
        formation_status = "skipped"

        if cluster_size >= MIN_FOUNDER_CLUSTER_SIZE:
            formation_status = "eligible_min_cluster"
        elif cluster_size == 1:
            singleton_reason = evaluate_singleton_exception(members[0])
            formation_status = (
                "singleton_exception" if singleton_reason else "singleton_below_threshold"
            )
        else:
            formation_status = "below_min_cluster"

        inventory.append(
            {
                "cluster_key": cluster_key,
                "mechanism_fingerprint": members[0].mechanism_fingerprint,
                "cluster_size": cluster_size,
                "formation_status": formation_status,
                "singleton_exception_reason": singleton_reason,
                "complaint_ids": [str(member.id) for member in members],
                "severities": [member.severity for member in members],
            }
        )
    return inventory


def _pattern_report(pattern) -> dict:
    return {
        "topic": pattern.topic,
        "cluster_key": pattern.anchor_phrase,
        "mechanism_fingerprint": pattern.mechanism_fingerprint,
        "founder_grouping_variant": pattern.founder_grouping_variant,
        "singleton_exception_reason": pattern.singleton_exception_reason,
        "complaint_ids": [str(complaint_id) for complaint_id in pattern.complaint_ids],
        "complaint_count": pattern.complaint_count,
        "pattern_source": pattern.pattern_source,
    }


def _fingerprint_inventory(evidence: list[ComplaintEvidence]) -> list[dict]:
    rows: list[dict] = []
    for member in (enrich_complaint_evidence(item) for item in evidence):
        fingerprint = member.mechanism_fingerprint or extract_mechanism_fingerprint(
            verbatim_quote=member.verbatim_quote,
            summary=member.summary,
        )
        rows.append(
            {
                "complaint_id": str(member.id),
                "mechanism_fingerprint": fingerprint,
                "severity": member.severity,
                "quote_specificity_passes": evaluate_singleton_exception(member) is not None
                if fingerprint
                else False,
                "business_function_code": member.business_function_code,
                "jtbd_code": member.jtbd_code,
                "consequence_code": member.consequence_code,
            }
        )
    return rows


async def main() -> int:
    signals_doc = _load_json(SIGNALS_CONFIG)
    corpus_doc = _load_json(CORPUS_CONFIG)
    signal_overrides = signals_doc["complaint_signals"]
    manual_themes = signals_doc["manual_themes"]
    lane_ids = set(signal_overrides.keys())

    init_db()
    factory = get_session_factory()
    async with factory() as session:
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
    close_db()

    lane_complaints = [complaint for complaint in complaints if str(complaint.id) in lane_ids]
    evidence = [_to_evidence(complaint, signal_overrides) for complaint in lane_complaints]

    min_cluster_size = MIN_FOUNDER_CLUSTER_SIZE
    phrase_patterns = TopicPatternDetector().detect(evidence, min_cluster_size=min_cluster_size)
    token_patterns = detect_token_clustering_patterns(evidence, min_cluster_size=min_cluster_size)
    venture_patterns = detect_venture_aware_patterns(
        evidence,
        min_cluster_size=min_cluster_size,
        emit_logs=False,
    )
    legacy_b_patterns = detect_founder_signal_patterns(
        evidence,
        min_cluster_size=min_cluster_size,
        variant="B",
        emit_logs=False,
    )
    production_patterns = resolve_generation_patterns(
        evidence,
        phrase_patterns,
        min_cluster_size=min_cluster_size,
    )

    cluster_inventory = _cluster_inventory(evidence)
    singleton_exceptions = [
        row for row in cluster_inventory if row["formation_status"] == "singleton_exception"
    ]

    report = {
        "experiment": "venture_aware_formation_stripe_billing",
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus": corpus_doc.get("experiment"),
        "lane_relevant_complaints": len(lane_complaints),
        "min_cluster_size": min_cluster_size,
        "baseline_comparison": {
            "phrase_patterns": len(phrase_patterns),
            "token_patterns": len(token_patterns),
            "legacy_variant_b_patterns": len(legacy_b_patterns),
            "venture_aware_patterns": len(venture_patterns),
            "production_resolve_patterns": len(production_patterns),
            "production_pattern_source": production_patterns[0].pattern_source
            if production_patterns
            else None,
            "production_grouping_variant": production_patterns[0].founder_grouping_variant
            if production_patterns
            else None,
        },
        "mechanism_fingerprint_inventory": _fingerprint_inventory(evidence),
        "cluster_inventory": cluster_inventory,
        "pattern_inventory": {
            "venture_aware": [_pattern_report(pattern) for pattern in venture_patterns],
            "legacy_variant_b": [_pattern_report(pattern) for pattern in legacy_b_patterns],
            "production": [_pattern_report(pattern) for pattern in production_patterns],
        },
        "singleton_exceptions": singleton_exceptions,
        "opportunity_inventory": {
            "patterns_eligible_for_generation": len(production_patterns),
            "singleton_exception_patterns": len(
                [pattern for pattern in production_patterns if pattern.singleton_exception_reason]
            ),
            "min_cluster_patterns": len(
                [pattern for pattern in production_patterns if not pattern.singleton_exception_reason]
            ),
            "expected_opportunities_if_one_per_pattern": len(production_patterns),
            "note": "Formation-only validation; opportunity LLM generation not invoked.",
        },
        "manual_theme_coverage": {
            theme_id: {
                "label": theme["label"],
                "complaint_ids": theme["complaint_ids"],
                "matched_production_patterns": [
                    pattern.anchor_phrase
                    for pattern in production_patterns
                    if set(UUID(cid) for cid in theme["complaint_ids"])
                    & set(pattern.complaint_ids)
                ],
            }
            for theme_id, theme in manual_themes.items()
        },
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    output_path = DOCS / "venture-aware-formation-validation-2026-06-05.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps(report, indent=2))
    print(f"\nWrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
