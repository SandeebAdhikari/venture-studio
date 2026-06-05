"""Tests for substantive-token pattern clustering (Pass 2)."""

from uuid import uuid4

from app.agents.opportunity.patterns import (
    PATTERN_SOURCE_TOKEN,
    TokenPatternDetector,
    TopicPatternDetector,
    detect_token_clustering_patterns,
)
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import (
    PATTERN_SOURCE_PHRASE,
    resolve_generation_patterns,
)


def _evidence(
    *,
    category_code: str = "workflow",
    domain_code: str = "devtools",
    persona_code: str = "developer",
    summary: str = "Pain point",
    quote: str,
    severity: int = 4,
) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary,
        verbatim_quote=quote,
        severity=severity,
        domain_code=domain_code,
        category_code=category_code,
        persona_code=persona_code,
        product_mentions=[],
    )


def test_detects_shared_substantive_token_cluster() -> None:
    evidence = [
        _evidence(
            quote=(
                f"Deploy pipeline breaks on step {index} for our monorepo service environment."
            ),
        )
        for index in range(4)
    ]

    patterns = detect_token_clustering_patterns(evidence, min_cluster_size=3)

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.pattern_source == PATTERN_SOURCE_TOKEN
    assert pattern.complaint_count >= 3
    anchor_tokens = set(pattern.anchor_phrase.split())
    assert len(anchor_tokens) >= 2
    assert anchor_tokens.issubset({"deploy", "pipeline", "monorepo", "service", "environment", "breaks", "step"})


def test_rejects_heterogeneous_token_cluster() -> None:
    evidence = [
        _evidence(
            quote="Software teams struggle with coordination across healthcare compliance workflows.",
            domain_code="healthcare",
            category_code="compliance",
        ),
        _evidence(
            quote="Software teams struggle with coordination across construction job sites.",
            domain_code="construction",
            category_code="operations",
        ),
        _evidence(
            quote="Software teams struggle with coordination for legal contract review automation.",
            domain_code="legal",
            category_code="documentation",
        ),
    ]

    assert detect_token_clustering_patterns(evidence, min_cluster_size=3) == []


def test_resolve_prefers_phrase_over_token() -> None:
    phrase_quote = "Staff scheduling breaks every week when staff call out sick."
    phrase_evidence = [
        _evidence(
            quote=phrase_quote,
            category_code="workflow",
            domain_code="saas_b2b",
            persona_code="ops_admin",
        )
        for _ in range(4)
    ]
    phrase_patterns = TopicPatternDetector().detect(phrase_evidence, min_cluster_size=3)
    assert phrase_patterns
    resolved = resolve_generation_patterns(phrase_evidence, phrase_patterns, min_cluster_size=3)
    assert resolved == phrase_patterns
    assert all(pattern.pattern_source == PATTERN_SOURCE_PHRASE for pattern in resolved)

    token_evidence = [
        _evidence(
            quote=f"Deploy pipeline breaks on step {index} for our monorepo service environment.",
        )
        for index in range(4)
    ]
    resolved_token = resolve_generation_patterns(token_evidence, [], min_cluster_size=3)
    assert len(resolved_token) == 1
    assert resolved_token[0].pattern_source == PATTERN_SOURCE_TOKEN


def test_disjoint_quotes_still_yield_no_patterns() -> None:
    disjoint_quotes = (
        "Checkout latency overwhelms shoppers during peak holiday weekends.",
        "Invoice rounding errors appear in nightly batch reconciliation jobs.",
        "Glacier storage dashboards hide critical quota warnings from admins.",
        "Piano tuner apps crash whenever bluetooth peripherals reconnect suddenly.",
        "Marble countertop vendors reject returns without photographic proof uploaded.",
    )
    evidence = [
        _evidence(
            category_code="ux_ui",
            domain_code="saas_b2c",
            persona_code="developer",
            quote=quote,
        )
        for quote in disjoint_quotes
    ]

    assert TopicPatternDetector().detect(evidence, min_cluster_size=3) == []
    assert TokenPatternDetector().detect(evidence, min_cluster_size=3) == []
    assert resolve_generation_patterns(evidence, [], min_cluster_size=3) == []
