#!/usr/bin/env python3
"""Evaluate founder-signal clustering variants A–D on the Stripe Billing corpus."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.opportunity.founder_signal_clustering import evaluate_founder_signal_variants
from app.agents.opportunity.patterns import TopicPatternDetector, detect_token_clustering_patterns
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import resolve_generation_patterns
from app.db.models.complaint import Complaint
from app.db.session import close_db, get_session_factory, init_db

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parents[1]
SIGNALS_CONFIG = API_ROOT / "config/collection_experiments/stripe_billing_founder_signals.json"
CORPUS_CONFIG = API_ROOT / "config/collection_experiments/stripe_billing_corpus.json"
DOCS = ROOT / "docs"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _jaccard(left: set[UUID], right: set[UUID]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _pattern_report(pattern) -> dict:
    return {
        "topic": pattern.topic,
        "cluster_key": pattern.anchor_phrase,
        "complaint_ids": [str(complaint_id) for complaint_id in pattern.complaint_ids],
        "complaint_count": pattern.complaint_count,
        "business_function_code": pattern.business_function_code,
        "jtbd_code": pattern.jtbd_code,
        "consequence_code": pattern.consequence_code,
    }


def _evaluate_variant(
    patterns: list,
    manual_themes: dict[str, dict],
    *,
    min_cluster_size: int,
) -> dict:
    theme_sets = {
        theme_id: {UUID(complaint_id) for complaint_id in theme["complaint_ids"]}
        for theme_id, theme in manual_themes.items()
    }
    recoverable_themes = {
        theme_id
        for theme_id, members in theme_sets.items()
        if len(members) >= min_cluster_size
    }

    pattern_sets = [set(pattern.complaint_ids) for pattern in patterns]
    theme_matches: list[dict] = []
    recovered: list[str] = []
    missed: list[str] = []
    junk: list[dict] = []

    for theme_id in sorted(theme_sets):
        members = theme_sets[theme_id]
        if theme_id not in recoverable_themes:
            continue

        best_pattern_idx = None
        best_jaccard = 0.0
        best_recall = 0.0
        for index, pattern_set in enumerate(pattern_sets):
            overlap = members & pattern_set
            if not overlap:
                continue
            jaccard = _jaccard(members, pattern_set)
            recall = len(overlap) / len(members)
            if jaccard > best_jaccard:
                best_jaccard = jaccard
                best_recall = recall
                best_pattern_idx = index

        theme_matches.append(
            {
                "theme_id": theme_id,
                "label": manual_themes[theme_id]["label"],
                "manual_size": len(members),
                "best_pattern_index": best_pattern_idx,
                "jaccard": round(best_jaccard, 3),
                "recall": round(best_recall, 3),
                "recovered": best_recall == 1.0 and best_jaccard == 1.0,
            }
        )
        if best_recall == 1.0 and best_jaccard == 1.0:
            recovered.append(theme_id)
        else:
            missed.append(theme_id)

    for index, pattern in enumerate(patterns):
        pattern_set = pattern_sets[index]
        matching_themes = [
            theme_id
            for theme_id, members in theme_sets.items()
            if pattern_set & members
        ]
        if len(matching_themes) > 1:
            junk.append(
                {
                    "pattern_index": index,
                    "cluster_key": pattern.anchor_phrase,
                    "matching_themes": matching_themes,
                    "reason": "spans multiple manual themes",
                }
            )
            continue

        if len(matching_themes) == 1:
            theme_id = matching_themes[0]
            if theme_id in recoverable_themes and pattern_set != theme_sets[theme_id]:
                junk.append(
                    {
                        "pattern_index": index,
                        "cluster_key": pattern.anchor_phrase,
                        "matching_themes": matching_themes,
                        "reason": "partial or superset match vs manual theme",
                    }
                )

    return {
        "pattern_count": len(patterns),
        "patterns": [_pattern_report(pattern) for pattern in patterns],
        "theme_overlap": theme_matches,
        "recovered_themes": recovered,
        "missed_themes": missed,
        "junk_patterns": junk,
        "exact_recovery_score": round(len(recovered) / len(recoverable_themes), 3)
        if recoverable_themes
        else 0.0,
    }


def _to_evidence(complaint: Complaint, signal_overrides: dict | None) -> ComplaintEvidence:
    override = (signal_overrides or {}).get(str(complaint.id), {})
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
    corpus_doc = _load_json(CORPUS_CONFIG)
    manual_themes = signals_doc["manual_themes"]
    signal_overrides = signals_doc["complaint_signals"]
    lane_ids = set(signal_overrides.keys())

    init_db()
    factory = get_session_factory()
    async with factory() as session:
        query = (
            select(Complaint)
            .options(
                selectinload(Complaint.category),
                selectinload(Complaint.domain),
                selectinload(Complaint.persona),
            )
            .order_by(Complaint.created_at.asc())
        )
        complaints = (await session.execute(query)).scalars().all()

    close_db()

    lane_complaints = [complaint for complaint in complaints if str(complaint.id) in lane_ids]
    evidence = [_to_evidence(complaint, signal_overrides) for complaint in lane_complaints]

    min_cluster_size = 3
    phrase_patterns = TopicPatternDetector().detect(evidence, min_cluster_size=min_cluster_size)
    token_patterns = detect_token_clustering_patterns(evidence, min_cluster_size=min_cluster_size)
    variant_results = evaluate_founder_signal_variants(evidence, min_cluster_size=min_cluster_size)
    production_patterns = resolve_generation_patterns(
        evidence,
        phrase_patterns,
        min_cluster_size=min_cluster_size,
    )

    evaluation = {
        "experiment": "founder_signal_clustering_stripe_billing",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        "corpus": corpus_doc.get("experiment"),
        "lane_relevant_complaints": len(lane_complaints),
        "baseline_passes": {
            "phrase_patterns": len(phrase_patterns),
            "token_patterns": len(token_patterns),
            "production_resolve_patterns": len(production_patterns),
            "production_pattern_source": production_patterns[0].pattern_source
            if production_patterns
            else None,
        },
        "variants": {
            variant: _evaluate_variant(
                patterns,
                manual_themes,
                min_cluster_size=min_cluster_size,
            )
            for variant, patterns in variant_results.items()
        },
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    output_path = DOCS / "founder-signal-clustering-stripe-billing-2026-06-05.json"
    output_path.write_text(json.dumps(evaluation, indent=2) + "\n")

    print(json.dumps(evaluation, indent=2))
    print(f"\nWrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
