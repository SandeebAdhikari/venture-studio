"""Deterministic founder-signal pattern detection (Pass 3)."""

from __future__ import annotations

from collections import Counter, defaultdict
from uuid import UUID

from app.agents.classification.founder_signals import (
    DEFAULT_FOUNDER_SIGNAL_VARIANT,
    FounderGroupingVariant,
    format_founder_cluster_key,
    validate_founder_signal_codes,
)
from app.agents.opportunity.patterns import MIN_DOMINANT_TAXONOMY_SHARE, derive_pattern_topic
from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern
from app.logging import get_logger

logger = get_logger(__name__)

PATTERN_SOURCE_FOUNDER_SIGNAL = "founder_signal_clustering"
MIN_FOUNDER_CLUSTER_SIZE = 3


def _format_signal_label(code: str) -> str:
    return " ".join(part.capitalize() for part in code.split("_"))


def _derive_founder_topic(
    *,
    cluster_key: str,
    business_function_code: str,
    jtbd_code: str | None,
    consequence_code: str | None,
    members: list[ComplaintEvidence],
) -> str:
    parts = [_format_signal_label(business_function_code)]
    if jtbd_code is not None:
        parts.append(_format_signal_label(jtbd_code))
    if consequence_code is not None:
        parts.append(_format_signal_label(consequence_code))
    if len(parts) >= 2:
        return " — ".join(parts[:3])
    return derive_pattern_topic(cluster_key.replace("|", " "), members)


def _grouping_components(
    member: ComplaintEvidence,
    variant: FounderGroupingVariant,
) -> tuple[str, str | None, str | None] | None:
    if (
        member.business_function_code is None
        or member.jtbd_code is None
        or member.consequence_code is None
    ):
        return None

    validated = validate_founder_signal_codes(
        business_function_code=member.business_function_code,
        jtbd_code=member.jtbd_code,
        consequence_code=member.consequence_code,
    )
    if validated is None:
        return None

    bf, jtbd, consequence = validated
    if variant == "A":
        return bf, None, None
    if variant == "B":
        return bf, jtbd, None
    if variant == "C":
        return bf, None, consequence
    return bf, jtbd, consequence


def _cluster_key(
    business_function_code: str,
    jtbd_code: str | None,
    consequence_code: str | None,
) -> str:
    return format_founder_cluster_key(
        business_function_code=business_function_code,
        jtbd_code=jtbd_code,
        consequence_code=consequence_code,
    )


def _passes_founder_coherence_gate(members: list[ComplaintEvidence]) -> bool:
    count = len(members)
    if count < MIN_FOUNDER_CLUSTER_SIZE:
        return False

    domain_counts = Counter(member.domain_code for member in members)
    top_domain_share = domain_counts.most_common(1)[0][1] / count
    return top_domain_share >= MIN_DOMINANT_TAXONOMY_SHARE


def _log_founder_signal_pattern(
    pattern: ComplaintPattern,
    *,
    variant: FounderGroupingVariant,
    business_function_code: str,
    jtbd_code: str | None,
    consequence_code: str | None,
) -> None:
    logger.info(
        "Founder signal pattern detected",
        extra={
            "pattern_source": "Founder Signal Clustering",
            "grouping_variant": variant,
            "cluster_key": pattern.anchor_phrase,
            "complaint_ids": [str(complaint_id) for complaint_id in pattern.complaint_ids],
            "business_function_code": business_function_code,
            "jtbd_code": jtbd_code,
            "consequence_code": consequence_code,
            "complaint_count": pattern.complaint_count,
        },
    )


def detect_founder_signal_patterns(
    evidence: list[ComplaintEvidence],
    *,
    min_cluster_size: int = MIN_FOUNDER_CLUSTER_SIZE,
    variant: FounderGroupingVariant = DEFAULT_FOUNDER_SIGNAL_VARIANT,
    emit_logs: bool = True,
) -> list[ComplaintPattern]:
    """Group complaints by stored founder signal enum codes (deterministic, no embeddings)."""
    if len(evidence) < min_cluster_size:
        return []

    keyed_members: dict[str, list[tuple[ComplaintEvidence, str, str | None, str | None]]] = (
        defaultdict(list)
    )

    for member in evidence:
        components = _grouping_components(member, variant)
        if components is None:
            continue
        bf, jtbd, consequence = components
        key = _cluster_key(bf, jtbd, consequence)
        keyed_members[key].append((member, bf, jtbd, consequence))

    patterns: list[ComplaintPattern] = []
    for cluster_key, bucket in sorted(
        keyed_members.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    ):
        members = [entry[0] for entry in bucket]
        if len(members) < min_cluster_size:
            continue
        if not _passes_founder_coherence_gate(members):
            continue

        bf = bucket[0][1]
        jtbd = bucket[0][2]
        consequence = bucket[0][3]
        domain_counts = Counter(member.domain_code for member in members)
        category_counts = Counter(member.category_code for member in members)
        persona_counts = Counter(member.persona_code for member in members)
        severities = [member.severity for member in members]

        pattern = ComplaintPattern(
            topic=_derive_founder_topic(
                cluster_key=cluster_key,
                business_function_code=bf,
                jtbd_code=jtbd,
                consequence_code=consequence,
                members=members,
            ),
            anchor_phrase=cluster_key,
            complaint_ids=[member.id for member in members],
            domain_code=domain_counts.most_common(1)[0][0],
            category_code=category_counts.most_common(1)[0][0],
            dominant_persona_code=persona_counts.most_common(1)[0][0],
            complaint_count=len(members),
            avg_severity=sum(severities) / len(severities),
            pattern_source=PATTERN_SOURCE_FOUNDER_SIGNAL,
            founder_grouping_variant=variant,
            business_function_code=bf,
            jtbd_code=jtbd,
            consequence_code=consequence,
        )
        if emit_logs:
            _log_founder_signal_pattern(
                pattern,
                variant=variant,
                business_function_code=bf,
                jtbd_code=jtbd,
                consequence_code=consequence,
            )
        patterns.append(pattern)

    return patterns


def evaluate_founder_signal_variants(
    evidence: list[ComplaintEvidence],
    *,
    min_cluster_size: int = MIN_FOUNDER_CLUSTER_SIZE,
) -> dict[FounderGroupingVariant, list[ComplaintPattern]]:
    """Run all grouping variants A–D without mutating production defaults."""
    return {
        variant: detect_founder_signal_patterns(
            evidence,
            min_cluster_size=min_cluster_size,
            variant=variant,
            emit_logs=False,
        )
        for variant in ("A", "B", "C", "D")
    }
