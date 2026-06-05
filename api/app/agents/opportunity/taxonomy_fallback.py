"""Bounded taxonomy fallback when phrase clustering yields zero patterns."""

from __future__ import annotations

from collections import Counter, defaultdict

from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern

MIN_FALLBACK_COMPLAINT_COUNT = 4
MIN_FALLBACK_DOMINANT_DOMAIN_SHARE = 0.5
MIN_FALLBACK_DOMINANT_PERSONA_SHARE = 0.4
MAX_FALLBACK_PATTERNS = 3

PATTERN_SOURCE_PHRASE = "phrase_clustering"
PATTERN_SOURCE_TAXONOMY = "taxonomy_fallback"


def format_taxonomy_label(code: str) -> str:
    """Deterministic display label from taxonomy code (e.g. workflow -> Workflow)."""
    return " ".join(part.capitalize() for part in code.split("_"))


def build_taxonomy_topic(category_code: str, domain_code: str) -> str:
    return f"{format_taxonomy_label(category_code)} — {format_taxonomy_label(domain_code)}"


def detect_taxonomy_fallback_patterns(
    evidence: list[ComplaintEvidence],
) -> list[ComplaintPattern]:
    """Group by category and emit up to MAX_FALLBACK_PATTERNS taxonomy-backed clusters."""
    if not evidence:
        return []

    by_category: dict[str, list[ComplaintEvidence]] = defaultdict(list)
    for member in evidence:
        by_category[member.category_code].append(member)

    candidates: list[tuple[int, ComplaintPattern]] = []

    for category_code, members in by_category.items():
        count = len(members)
        if count < MIN_FALLBACK_COMPLAINT_COUNT:
            continue

        domain_counts = Counter(member.domain_code for member in members)
        persona_counts = Counter(member.persona_code for member in members)
        domain_code, domain_n = domain_counts.most_common(1)[0]
        persona_code, persona_n = persona_counts.most_common(1)[0]
        domain_share = domain_n / count
        persona_share = persona_n / count

        if domain_share < MIN_FALLBACK_DOMINANT_DOMAIN_SHARE:
            continue
        if persona_share < MIN_FALLBACK_DOMINANT_PERSONA_SHARE:
            continue

        topic = build_taxonomy_topic(category_code, domain_code)
        pattern = ComplaintPattern(
            topic=topic,
            anchor_phrase=f"{category_code}|{domain_code}",
            complaint_ids=[member.id for member in members],
            domain_code=domain_code,
            category_code=category_code,
            dominant_persona_code=persona_code,
            complaint_count=count,
            avg_severity=sum(member.severity for member in members) / count,
            pattern_source=PATTERN_SOURCE_TAXONOMY,
        )
        candidates.append((count, pattern))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [pattern for _, pattern in candidates[:MAX_FALLBACK_PATTERNS]]


def resolve_generation_patterns(
    evidence: list[ComplaintEvidence],
    phrase_patterns: list[ComplaintPattern],
) -> list[ComplaintPattern]:
    """Return phrase clusters when present; otherwise bounded taxonomy fallback."""
    if phrase_patterns:
        return phrase_patterns
    return detect_taxonomy_fallback_patterns(evidence)
