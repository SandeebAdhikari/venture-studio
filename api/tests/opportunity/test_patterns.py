"""Unit tests for topic pattern detection and venture-quality clustering."""

from uuid import uuid4

import pytest

from app.agents.opportunity.patterns import (
    TopicPatternDetector,
    clustering_source_text,
    derive_pattern_topic,
    is_boilerplate_phrase,
    is_weak_anchor_phrase,
    passes_coherence_gate,
    passes_semantic_overlap_gate,
)
from app.agents.opportunity.schemas import ComplaintEvidence


def _complaint(
    *,
    summary: str,
    verbatim_quote: str,
    severity: int = 4,
    domain_code: str = "saas_b2b",
    category_code: str = "workflow",
    persona_code: str = "ops_admin",
) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary,
        verbatim_quote=verbatim_quote,
        severity=severity,
        domain_code=domain_code,
        category_code=category_code,
        persona_code=persona_code,
        product_mentions=[],
    )


def test_boilerplate_phrase_suppression() -> None:
    assert is_boilerplate_phrase("user expresses frustration")
    assert is_boilerplate_phrase("expresses frustration")
    assert is_boilerplate_phrase("user frustrated")
    assert is_boilerplate_phrase("seeking advice")
    assert not is_boilerplate_phrase("deployment environment complexity")
    assert not is_boilerplate_phrase("package dependency management")


def test_clustering_prefers_verbatim_over_classifier_summary() -> None:
    complaint = _complaint(
        summary="The user expresses frustration with deployment environment complexity.",
        verbatim_quote="Every deploy fails because node versions drift between machines.",
    )
    text = clustering_source_text(complaint)
    assert "deploy" in text
    assert "node" in text
    assert "expresses frustration" not in text


def test_detects_staff_scheduling_pattern() -> None:
    quote = "Staff scheduling breaks every week when staff call out sick."
    complaints = [
        _complaint(
            summary="The user expresses frustration with scheduling.",
            verbatim_quote=quote,
        )
        for _ in range(5)
    ]
    complaints.append(
        _complaint(
            summary="Pricing is unrelated and should not dominate the batch.",
            verbatim_quote="Pricing is too expensive for our small team right now.",
            severity=2,
        )
    )

    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)

    assert len(patterns) >= 1
    top = max(patterns, key=lambda item: item.complaint_count)
    assert top.complaint_count >= 3
    assert "User" not in top.topic
    assert "Frustration" not in top.topic
    assert "scheduling" in top.topic.lower() or "staff" in top.topic.lower()


def test_suppresses_generic_summary_boilerplate_cluster() -> None:
    """L1/L2: Classifier summaries share boilerplate but verbatims do not."""
    complaints = [
        _complaint(
            summary="The user expresses frustration over remote work opportunities.",
            verbatim_quote="I cannot find remote software engineering roles in my city.",
        ),
        _complaint(
            summary="The user expresses frustration with App Store Connect.",
            verbatim_quote="App Store Connect rejects builds with cryptic provisioning errors.",
        ),
        _complaint(
            summary="The user is frustrated by dependency sprawl.",
            verbatim_quote="Installing packages for every project wastes hours every week.",
        ),
        _complaint(
            summary="The user expresses frustration with documentation quality.",
            verbatim_quote="Official docs skip the steps needed for production deployments.",
        ),
    ]
    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)
    assert not any("expresses frustration" in pattern.topic.lower() for pattern in patterns)
    assert patterns == []


def test_clusters_real_shared_verbatim_topic() -> None:
    quote = "Package dependency management is a nightmare for our monorepo builds."
    complaints = [
        _complaint(
            summary="The user expresses frustration with tooling.",
            verbatim_quote=quote,
            category_code="workflow",
            domain_code="saas_b2b",
        )
        for _ in range(4)
    ]

    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.complaint_count == 4
    assert "User Expresses" not in pattern.topic
    assert "Dependency" in pattern.topic and "Management" in pattern.topic


def test_rejects_heterogeneous_taxonomy_cluster() -> None:
    """L4: Shared incidental phrase with scattered domains/categories is rejected."""
    shared = "software teams struggle with coordination across tools"
    complaints = [
        _complaint(
            summary="Summary one",
            verbatim_quote=f"{shared} in healthcare compliance workflows.",
            domain_code="healthcare",
            category_code="compliance",
        ),
        _complaint(
            summary="Summary two",
            verbatim_quote=f"{shared} when managing construction job sites.",
            domain_code="construction",
            category_code="operations",
        ),
        _complaint(
            summary="Summary three",
            verbatim_quote=f"{shared} for legal contract review automation.",
            domain_code="legal",
            category_code="documentation",
        ),
    ]
    assert not passes_coherence_gate("software teams struggle", complaints)

    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)
    assert patterns == []


def test_pattern_naming_uses_business_language() -> None:
    members = [
        _complaint(
            summary="The user expresses frustration.",
            verbatim_quote="Deployment environment complexity slows every release pipeline.",
        ),
        _complaint(
            summary="The user is frustrated.",
            verbatim_quote="Our deployment environments never match between staging and prod.",
        ),
    ]
    topic = derive_pattern_topic("deployment environment", members)
    assert "Deployment Environment" in topic
    assert "User Expresses Frustration" != topic


def test_weak_anchor_rejects_pronoun_bigram() -> None:
    assert is_weak_anchor_phrase("i find")
    assert is_weak_anchor_phrase("don t")


def test_rejects_pronoun_anchor_clusters() -> None:
    complaints = [
        _complaint(
            summary="Code coupling",
            verbatim_quote="Often I find parts of code that affect unrelated modules.",
        ),
        _complaint(
            summary="Search quality",
            verbatim_quote="I find myself frustrated with google search omitting results.",
        ),
        _complaint(
            summary="Hiring trust",
            verbatim_quote="I find it baffling they hired me if they will not trust my work.",
        ),
    ]
    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)
    assert patterns == []


def test_rejects_contraction_fragment_clusters() -> None:
    complaints = [
        _complaint(
            summary="Slow process",
            verbatim_quote="I am frustrated, I don&#x27;t understand why everything takes so long.",
            domain_code="devtools",
            category_code="other",
        ),
        _complaint(
            summary="Apple notifications",
            verbatim_quote="Please add purchase notifications Apple, I don&#x27;t want RevenueCat.",
            domain_code="saas_b2c",
            category_code="ux_ui",
        ),
        _complaint(
            summary="Lost tooling",
            verbatim_quote="We had a nice ecosystem of tools. Now we don&#x27;t anymore.",
            domain_code="devtools",
            category_code="missing_feature",
        ),
    ]
    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)
    assert patterns == []


def test_semantic_overlap_gate_requires_shared_substance() -> None:
    members = [
        _complaint(
            summary="One",
            verbatim_quote="I find parts of code that break unrelated modules daily.",
        ),
        _complaint(
            summary="Two",
            verbatim_quote="I find google search frustrating when it hides the best answers.",
        ),
        _complaint(
            summary="Three",
            verbatim_quote="I find hiring decisions baffling when leadership ignores engineers.",
        ),
    ]
    assert not passes_semantic_overlap_gate("i find", members)


def test_derive_topic_falls_back_to_taxonomy_for_weak_anchors() -> None:
    members = [
        _complaint(
            summary="Frustration",
            verbatim_quote="Deployment pipelines fail when node versions drift between machines.",
            domain_code="saas_b2b",
            category_code="workflow",
        ),
        _complaint(
            summary="Frustration two",
            verbatim_quote="Our deployment environments never match between staging and production.",
            domain_code="saas_b2b",
            category_code="workflow",
        ),
    ]
    topic = derive_pattern_topic("deployment environment", members)
    assert "Deployment" in topic and "Environment" in topic


def test_returns_empty_when_below_min_cluster_size() -> None:
    complaints = [
        _complaint(
            summary="Staff scheduling is hard.",
            verbatim_quote="Staff scheduling fails on weekends for our team.",
        ),
        _complaint(
            summary="Staff scheduling fails.",
            verbatim_quote="Weekend staff scheduling is still manual for us.",
        ),
    ]
    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)
    assert patterns == []
