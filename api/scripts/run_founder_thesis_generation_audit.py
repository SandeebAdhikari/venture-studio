#!/usr/bin/env python3
"""Audit opportunity generation against clean manual R1/R2/R3 patterns."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.opportunity.graph import OpportunityGeneratorAgent
from app.agents.opportunity.llm_client import OpenAIOpportunityClient
from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern
from app.config import get_settings
from app.db.models.complaint import Complaint
from app.db.session import close_db, get_session_factory, init_db

API_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[2]
SIGNALS_CONFIG = API_ROOT / "config/collection_experiments/stripe_billing_founder_signals.json"
DOCS = ROOT / "docs"

MANUAL_PATTERNS: dict[str, dict[str, object]] = {
    "R1": {
        "label": "Processor Access",
        "complaint_id_prefixes": [
            "191e82f8",
            "c80adb68",
            "a4d30dbe",
            "7e1446aa",
        ],
        "topic": "Payment Processor — Accept Payments",
        "anchor_phrase": "payment_processor|accept_payments",
        "business_function_code": "payment_processor",
        "jtbd_code": "accept_payments",
        "consequence_code": None,
    },
    "R2": {
        "label": "Fraud / Disputes",
        "complaint_id_prefixes": [
            "948e6176",
            "57577e0b",
            "df278195",
        ],
        "topic": "Fraud Prevention — Prevent Fraud",
        "anchor_phrase": "fraud_prevention|prevent_fraud",
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": None,
    },
    "R3": {
        "label": "Billing Model Infrastructure",
        "complaint_id_prefixes": [
            "4281360c",
            "988dadac",
            "4e3de199",
        ],
        "topic": "Billing Model Infrastructure",
        "anchor_phrase": "billing_model_infrastructure",
        "business_function_code": "billing_operations",
        "jtbd_code": "automate_billing",
        "consequence_code": None,
    },
}


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


def _build_pattern(
    spec: dict[str, object],
    evidence: list[ComplaintEvidence],
) -> ComplaintPattern:
    domain_counts = Counter(item.domain_code for item in evidence)
    category_counts = Counter(item.category_code for item in evidence)
    persona_counts = Counter(item.persona_code for item in evidence)
    severities = [item.severity for item in evidence]
    return ComplaintPattern(
        topic=str(spec["topic"]),
        anchor_phrase=str(spec["anchor_phrase"]),
        complaint_ids=[item.id for item in evidence],
        domain_code=domain_counts.most_common(1)[0][0],
        category_code=category_counts.most_common(1)[0][0],
        dominant_persona_code=persona_counts.most_common(1)[0][0],
        complaint_count=len(evidence),
        avg_severity=sum(severities) / len(severities),
        pattern_source="founder_signal_clustering",
        founder_grouping_variant="B",
        business_function_code=str(spec["business_function_code"])
        if spec.get("business_function_code")
        else None,
        jtbd_code=str(spec["jtbd_code"]) if spec.get("jtbd_code") else None,
        consequence_code=str(spec["consequence_code"])
        if spec.get("consequence_code")
        else None,
    )


async def main() -> int:
    signals_doc = _load_json(SIGNALS_CONFIG)
    signal_overrides = signals_doc["complaint_signals"]
    all_prefixes = {
        prefix
        for spec in MANUAL_PATTERNS.values()
        for prefix in spec["complaint_id_prefixes"]  # type: ignore[union-attr]
    }

    init_db()
    factory = get_session_factory()
    settings = get_settings()
    agent = OpportunityGeneratorAgent(
        OpenAIOpportunityClient(settings),
        settings,
    )

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
        by_prefix = {
            str(complaint.id)[:8]: complaint
            for complaint in complaints
            if str(complaint.id)[:8] in all_prefixes
        }

        results = []
        for theme_id, spec in MANUAL_PATTERNS.items():
            evidence = [
                _to_evidence(by_prefix[prefix], signal_overrides)
                for prefix in spec["complaint_id_prefixes"]  # type: ignore[index]
            ]
            pattern = _build_pattern(spec, evidence)
            generation = await agent.run(pattern, evidence)
            draft = generation.draft
            llm = draft or {}
            output = None
            if draft is not None:
                output = {
                    "title": draft.title,
                    "problem_statement": draft.problem_statement,
                    "explanation": draft.explanation,
                    "confidence_score": draft.confidence_score,
                    "target_user": draft.target_user,
                    "frequency_signal": draft.frequency_signal,
                    "existing_alternatives": draft.existing_alternatives,
                    "gap": draft.gap,
                }
            results.append(
                {
                    "theme_id": theme_id,
                    "label": spec["label"],
                    "pattern": pattern.model_dump(mode="json"),
                    "evidence": [
                        {
                            "id": str(item.id)[:8],
                            "summary": item.summary,
                            "quote": item.verbatim_quote,
                            "severity": item.severity,
                            "domain_code": item.domain_code,
                            "persona_code": item.persona_code,
                            "product_mentions": item.product_mentions,
                        }
                        for item in evidence
                    ],
                    "generation_status": generation.status,
                    "skip_reason": generation.skip_reason,
                    "error": generation.error,
                    "validation_errors": generation.error,
                    "attempts": generation.attempts,
                    "output": output,
                }
            )

    await close_db()

    report = {
        "experiment": "founder_thesis_generation_audit",
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus": "stripe_billing",
        "patterns": results,
    }
    DOCS.mkdir(parents=True, exist_ok=True)
    output_path = DOCS / "founder-thesis-generation-audit-2026-06-05.json"
    output_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))
    print(f"\nWrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
