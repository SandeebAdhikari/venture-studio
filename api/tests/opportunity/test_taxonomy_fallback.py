"""Tests for bounded taxonomy fallback pattern detection."""

from uuid import uuid4

from app.agents.opportunity.patterns import TopicPatternDetector
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import (
    MAX_FALLBACK_PATTERNS,
    PATTERN_SOURCE_PHRASE,
    PATTERN_SOURCE_TAXONOMY,
    build_taxonomy_topic,
    detect_taxonomy_fallback_patterns,
    resolve_generation_patterns,
)


def _evidence(
    *,
    category_code: str = "workflow",
    domain_code: str = "devtools",
    persona_code: str = "developer",
    summary: str = "Pain point",
    quote: str | None = None,
) -> ComplaintEvidence:
    quote = quote or summary
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary,
        verbatim_quote=quote,
        severity=4,
        domain_code=domain_code,
        category_code=category_code,
        persona_code=persona_code,
        product_mentions=[],
    )


def _workflow_devtools_batch(count: int) -> list[ComplaintEvidence]:
    return [
        _evidence(
            category_code="workflow",
            domain_code="devtools",
            persona_code="developer",
            summary=f"Deployment pain variant {index}",
            quote=f"Deploy pipeline breaks on step {index} for our monorepo service.",
        )
        for index in range(count)
    ]


def test_phrase_patterns_found_fallback_not_used() -> None:
    quote = "Staff scheduling breaks every week when staff call out sick."
    evidence = [
        _evidence(
            summary="Scheduling frustration",
            quote=quote,
            category_code="workflow",
            domain_code="saas_b2b",
        )
        for _ in range(4)
    ]
    phrase_patterns = TopicPatternDetector().detect(evidence, min_cluster_size=3)
    assert len(phrase_patterns) >= 1
    assert all(p.pattern_source == PATTERN_SOURCE_PHRASE for p in phrase_patterns)

    resolved = resolve_generation_patterns(evidence, phrase_patterns)
    assert resolved == phrase_patterns
    assert not any(p.pattern_source == PATTERN_SOURCE_TAXONOMY for p in resolved)


def test_no_phrase_patterns_fallback_rejects_incoherent_bucket() -> None:
    """Diverse HN-like quotes: no phrase cluster; fallback fails coherence gate."""
    evidence = []
    disjoint_quotes = (
        "Checkout latency overwhelms shoppers during peak holiday weekends.",
        "Invoice rounding errors appear in nightly batch reconciliation jobs.",
        "Glacier storage dashboards hide critical quota warnings from admins.",
        "Piano tuner apps crash whenever bluetooth peripherals reconnect suddenly.",
        "Marble countertop vendors reject returns without photographic proof uploaded.",
    )
    for index, quote in enumerate(disjoint_quotes):
        evidence.append(
            _evidence(
                category_code="ux_ui",
                domain_code="saas_b2c",
                persona_code="developer",
                summary=f"Unrelated UX issue {index}",
                quote=quote,
            )
        )

    phrase_patterns = TopicPatternDetector().detect(evidence, min_cluster_size=3)
    assert phrase_patterns == []

    fallback = detect_taxonomy_fallback_patterns(evidence)
    assert fallback == []

    resolved = resolve_generation_patterns(evidence, phrase_patterns)
    assert resolved == []


def test_complaint_count_threshold_enforced() -> None:
    evidence = _workflow_devtools_batch(3)
    assert detect_taxonomy_fallback_patterns(evidence) == []


def test_dominant_domain_threshold_enforced() -> None:
    """Four distinct domains in one category → no domain reaches 50%."""
    evidence = [
        _evidence(category_code="workflow", domain_code="devtools", persona_code="developer"),
        _evidence(category_code="workflow", domain_code="saas_b2b", persona_code="developer"),
        _evidence(category_code="workflow", domain_code="ops_it", persona_code="developer"),
        _evidence(category_code="workflow", domain_code="fintech", persona_code="developer"),
    ]
    assert detect_taxonomy_fallback_patterns(evidence) == []


def test_dominant_persona_threshold_enforced() -> None:
    """Four distinct personas in one category → top persona share is 25%."""
    evidence = [
        _evidence(category_code="workflow", domain_code="devtools", persona_code="developer"),
        _evidence(category_code="workflow", domain_code="devtools", persona_code="founder"),
        _evidence(category_code="workflow", domain_code="devtools", persona_code="ops_admin"),
        _evidence(category_code="workflow", domain_code="devtools", persona_code="product_manager"),
    ]
    assert detect_taxonomy_fallback_patterns(evidence) == []


def test_maximum_three_patterns_enforced() -> None:
    evidence: list[ComplaintEvidence] = []
    categories = ("workflow", "performance", "security", "support", "ux_ui")
    for category in categories:
        for index in range(4):
            evidence.append(
                _evidence(
                    category_code=category,
                    domain_code="devtools",
                    persona_code="developer",
                    summary=f"{category} deploy pipeline pain {index}",
                    quote=(
                        f"Deploy pipeline breaks during {category} release step {index} "
                        "for our monorepo service environment."
                    ),
                )
            )

    patterns = detect_taxonomy_fallback_patterns(evidence)
    assert len(patterns) == MAX_FALLBACK_PATTERNS
    assert all(p.pattern_source == PATTERN_SOURCE_TAXONOMY for p in patterns)


def test_pattern_source_metadata_populated() -> None:
    evidence = _workflow_devtools_batch(4)
    patterns = detect_taxonomy_fallback_patterns(evidence)
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.pattern_source == PATTERN_SOURCE_TAXONOMY
    assert pattern.topic == "Workflow — Devtools"
    assert pattern.anchor_phrase == "workflow|devtools"
    assert pattern.category_code == "workflow"
    assert pattern.domain_code == "devtools"
