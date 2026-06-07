"""Venture-aware founder signal clustering (mechanism fingerprints + singleton exceptions)."""

from __future__ import annotations

from collections import Counter, defaultdict

from app.agents.classification.founder_signals import (
    format_venture_cluster_key,
    validate_founder_signal_codes,
)
from app.agents.opportunity.founder_signal_clustering import (
    MIN_FOUNDER_CLUSTER_SIZE,
    PATTERN_SOURCE_FOUNDER_SIGNAL,
    _derive_founder_topic,
    _passes_founder_coherence_gate,
)
from app.agents.classification.signal_overlays import enrich_complaint_evidence_with_overlay
from app.agents.opportunity.mechanism_fingerprints import evaluate_singleton_exception
from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern
from app.logging import get_logger

logger = get_logger(__name__)

VENTURE_AWARE_GROUPING_VARIANT = "E"


def _log_venture_pattern(
    pattern: ComplaintPattern,
    *,
    cluster_key: str,
    cluster_size: int,
    singleton_exception_reason: str | None,
) -> None:
    mechanism = pattern.mechanism_fingerprint or "unknown"
    payload = {
        "pattern_source": "Venture-Aware Clustering",
        "grouping_variant": VENTURE_AWARE_GROUPING_VARIANT,
        "cluster_key": cluster_key,
        "mechanism_fingerprint": mechanism,
        "cluster_size": cluster_size,
        "singleton_exception_reason": singleton_exception_reason,
        "complaint_ids": [str(complaint_id) for complaint_id in pattern.complaint_ids],
        "complaint_count": pattern.complaint_count,
    }
    if singleton_exception_reason:
        logger.info("Venture-aware singleton exception pattern formed", extra=payload)
    else:
        logger.info("Venture-aware cluster pattern formed", extra=payload)


def _build_venture_pattern(
    members: list[ComplaintEvidence],
    cluster_key: str,
    singleton_exception_reason: str | None,
) -> ComplaintPattern:
    bf = members[0].business_function_code
    jtbd = members[0].jtbd_code
    consequence = members[0].consequence_code
    mechanism = members[0].mechanism_fingerprint

    domain_counts = Counter(member.domain_code for member in members)
    category_counts = Counter(member.category_code for member in members)
    persona_counts = Counter(member.persona_code for member in members)
    severities = [member.severity for member in members]

    return ComplaintPattern(
        topic=_derive_founder_topic(
            cluster_key=cluster_key,
            business_function_code=bf or "",
            jtbd_code=jtbd,
            consequence_code=consequence,
            members=members,
            mechanism_fingerprint=mechanism,
        ),
        anchor_phrase=cluster_key,
        complaint_ids=[member.id for member in members],
        domain_code=domain_counts.most_common(1)[0][0],
        category_code=category_counts.most_common(1)[0][0],
        dominant_persona_code=persona_counts.most_common(1)[0][0],
        complaint_count=len(members),
        avg_severity=sum(severities) / len(severities),
        pattern_source=PATTERN_SOURCE_FOUNDER_SIGNAL,
        founder_grouping_variant=VENTURE_AWARE_GROUPING_VARIANT,
        business_function_code=bf,
        jtbd_code=jtbd,
        consequence_code=consequence,
        mechanism_fingerprint=mechanism,
        singleton_exception_reason=singleton_exception_reason,
    )


def _append_singleton_patterns(
    patterns: list[ComplaintPattern],
    members: list[ComplaintEvidence],
    cluster_key: str,
    *,
    emit_logs: bool,
) -> None:
    """Evaluate each member independently — used for size-1 and size-2 clusters."""
    for member in members:
        singleton_exception_reason = evaluate_singleton_exception(member)
        if singleton_exception_reason is None:
            continue
        pattern = _build_venture_pattern(
            [member],
            cluster_key,
            singleton_exception_reason,
        )
        if emit_logs:
            _log_venture_pattern(
                pattern,
                cluster_key=cluster_key,
                cluster_size=1,
                singleton_exception_reason=singleton_exception_reason,
            )
        patterns.append(pattern)


def detect_venture_aware_patterns(
    evidence: list[ComplaintEvidence],
    *,
    min_cluster_size: int = MIN_FOUNDER_CLUSTER_SIZE,
    emit_logs: bool = True,
) -> list[ComplaintPattern]:
    """Group complaints by BF+JTBD+consequence+mechanism with singleton exceptions."""
    if not evidence:
        return []

    enriched = [enrich_complaint_evidence_with_overlay(member) for member in evidence]
    keyed_members: dict[str, list[ComplaintEvidence]] = defaultdict(list)

    for member in enriched:
        if (
            member.business_function_code is None
            or member.jtbd_code is None
            or member.consequence_code is None
            or member.mechanism_fingerprint is None
        ):
            continue

        validated = validate_founder_signal_codes(
            business_function_code=member.business_function_code,
            jtbd_code=member.jtbd_code,
            consequence_code=member.consequence_code,
        )
        if validated is None:
            continue

        bf, jtbd, consequence = validated
        cluster_key = format_venture_cluster_key(
            business_function_code=bf,
            jtbd_code=jtbd,
            consequence_code=consequence,
            mechanism_fingerprint=member.mechanism_fingerprint,
        )
        keyed_members[cluster_key].append(member)

    patterns: list[ComplaintPattern] = []
    for cluster_key, members in sorted(
        keyed_members.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    ):
        cluster_size = len(members)

        if cluster_size >= min_cluster_size:
            if not _passes_founder_coherence_gate(members):
                continue
            pattern = _build_venture_pattern(members, cluster_key, None)
            if emit_logs:
                _log_venture_pattern(
                    pattern,
                    cluster_key=cluster_key,
                    cluster_size=cluster_size,
                    singleton_exception_reason=None,
                )
            patterns.append(pattern)
        elif cluster_size in {1, 2}:
            # Size 2: evaluate singleton eligibility per member instead of rejecting both.
            _append_singleton_patterns(
                patterns,
                members,
                cluster_key,
                emit_logs=emit_logs,
            )

    return patterns
