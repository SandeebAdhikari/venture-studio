"""Deterministic recurring-topic detection from classified complaints."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from uuid import UUID

from app.agents.classification.source_text import normalize_for_verbatim_grounding
from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "can",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "their",
        "they",
        "this",
        "to",
        "too",
        "we",
        "with",
        "you",
        "your",
    }
)

# L1: classifier / clustering boilerplate phrases (normalized substring match).
BLOCKED_CLUSTER_PHRASES: frozenset[str] = frozenset(
    {
        "user expresses frustration",
        "expresses frustration",
        "user frustrated",
        "user is frustrated",
        "the user expresses frustration",
        "the user is frustrated",
        "seeking advice",
        "user seeking advice",
        "expresses frustration with",
        "user expresses",
    }
)

BOILERPLATE_TOPIC_TOKENS: frozenset[str] = frozenset(
    {
        "user",
        "users",
        "expresses",
        "expressing",
        "frustration",
        "frustrated",
        "seeking",
        "advice",
        "complaint",
        "complaints",
        "issue",
        "issues",
        "problem",
        "problems",
    }
)

CLASSIFIER_SUMMARY_PREFIXES: tuple[str, ...] = (
    "the user expresses frustration",
    "the user is frustrated",
    "the user frustrated",
    "user expresses frustration",
    "user is frustrated",
)

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# L4: minimum share for dominant domain or category code in a cluster.
MIN_DOMINANT_TAXONOMY_SHARE = 0.5
# Reject when taxonomy labels are highly scattered across a larger cluster.
MAX_TAXONOMY_LABELS_FOR_STRICT_GATE = 2

MIN_VERBATIM_WORDS_FOR_CLUSTERING = 4


def _normalize_text(text: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(text.lower()))


def _extract_phrases(text: str, *, n: int) -> set[str]:
    tokens = [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOPWORDS]
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


def is_boilerplate_phrase(phrase: str) -> bool:
    """L1: True when phrase is generic classifier clustering noise."""
    normalized = _normalize_text(phrase)
    if not normalized or len(normalized.split()) < 2:
        return True

    if normalized in BLOCKED_CLUSTER_PHRASES:
        return True

    for blocked in BLOCKED_CLUSTER_PHRASES:
        if blocked in normalized or normalized in blocked:
            return True

    tokens = normalized.split()
    if tokens and all(token in BOILERPLATE_TOPIC_TOKENS for token in tokens):
        return True

    return False


def _is_classifier_boilerplate_summary(summary: str) -> bool:
    normalized = _normalize_text(normalize_for_verbatim_grounding(summary))
    return any(normalized.startswith(prefix) for prefix in CLASSIFIER_SUMMARY_PREFIXES)


def clustering_source_text(complaint: ComplaintEvidence) -> str:
    """L2: Prefer grounded verbatim language over classifier summary boilerplate."""
    quote = normalize_for_verbatim_grounding(complaint.verbatim_quote)
    quote_normalized = _normalize_text(quote)
    quote_words = len(quote_normalized.split())

    if quote_words >= MIN_VERBATIM_WORDS_FOR_CLUSTERING:
        return quote_normalized

    summary = normalize_for_verbatim_grounding(complaint.summary)
    if _is_classifier_boilerplate_summary(summary):
        return quote_normalized

    summary_normalized = _normalize_text(summary)
    if quote_words > 0:
        return quote_normalized
    return summary_normalized


def passes_coherence_gate(anchor_phrase: str, members: list[ComplaintEvidence]) -> bool:
    """L4: Reject heterogeneous or taxonomy-scattered clusters (deterministic)."""
    if is_boilerplate_phrase(anchor_phrase):
        return False

    count = len(members)
    if count == 0:
        return False

    domain_counts = Counter(member.domain_code for member in members)
    category_counts = Counter(member.category_code for member in members)
    top_domain_share = domain_counts.most_common(1)[0][1] / count
    top_category_share = category_counts.most_common(1)[0][1] / count

    if top_domain_share < MIN_DOMINANT_TAXONOMY_SHARE and top_category_share < MIN_DOMINANT_TAXONOMY_SHARE:
        return False

    if count >= 4:
        domain_labels = len(domain_counts)
        category_labels = len(category_counts)
        if (
            domain_labels > MAX_TAXONOMY_LABELS_FOR_STRICT_GATE
            and category_labels > MAX_TAXONOMY_LABELS_FOR_STRICT_GATE
            and top_domain_share < 0.6
            and top_category_share < 0.6
        ):
            return False

    return True


def derive_pattern_topic(anchor_phrase: str, members: list[ComplaintEvidence]) -> str:
    """M4: Name patterns from substantive grounded language, not classifier boilerplate."""
    if not is_boilerplate_phrase(anchor_phrase):
        anchor_tokens = [
            token
            for token in anchor_phrase.split()
            if token not in STOPWORDS and token not in BOILERPLATE_TOPIC_TOKENS
        ]
        if len(anchor_tokens) >= 2:
            return " ".join(token.capitalize() for token in anchor_tokens[:4])

    token_counts = Counter()
    for member in members:
        for token in TOKEN_PATTERN.findall(clustering_source_text(member)):
            if token in STOPWORDS or token in BOILERPLATE_TOPIC_TOKENS or len(token) < 3:
                continue
            token_counts[token] += 1

    ranked = [token for token, _ in token_counts.most_common(6)]
    if len(ranked) >= 2:
        return " ".join(token.capitalize() for token in ranked[:3])

    if len(ranked) == 1:
        return f"{ranked[0].capitalize()} Workflow Pain"

    return "Recurring Customer Pain"


class TopicPatternDetector:
    """Groups complaints by repeated phrases in grounded complaint evidence."""

    def detect(
        self,
        complaints: list[ComplaintEvidence],
        *,
        min_cluster_size: int,
    ) -> list[ComplaintPattern]:
        if len(complaints) < min_cluster_size:
            return []

        phrase_to_ids: dict[str, set[UUID]] = defaultdict(set)
        complaints_by_id = {complaint.id: complaint for complaint in complaints}

        for complaint in complaints:
            source_text = clustering_source_text(complaint)
            if not source_text:
                continue
            phrases = _extract_phrases(source_text, n=2) | _extract_phrases(source_text, n=3)
            for phrase in phrases:
                if is_boilerplate_phrase(phrase):
                    continue
                phrase_to_ids[phrase].add(complaint.id)

        eligible_phrases = [
            phrase
            for phrase, member_ids in phrase_to_ids.items()
            if len(member_ids) >= min_cluster_size and not is_boilerplate_phrase(phrase)
        ]
        eligible_phrases.sort(
            key=lambda phrase: (len(phrase_to_ids[phrase]), len(phrase)),
            reverse=True,
        )

        assigned: set[UUID] = set()
        patterns: list[ComplaintPattern] = []

        for phrase in eligible_phrases:
            member_ids = [
                complaint_id
                for complaint_id in phrase_to_ids[phrase]
                if complaint_id not in assigned
            ]
            if len(member_ids) < min_cluster_size:
                continue

            members = [complaints_by_id[complaint_id] for complaint_id in member_ids]
            if not passes_coherence_gate(phrase, members):
                continue

            for complaint_id in member_ids:
                assigned.add(complaint_id)

            patterns.append(self._build_pattern(phrase, members))

        return patterns

    @staticmethod
    def _build_pattern(anchor_phrase: str, members: list[ComplaintEvidence]) -> ComplaintPattern:
        domain_counts = Counter(member.domain_code for member in members)
        category_counts = Counter(member.category_code for member in members)
        persona_counts = Counter(member.persona_code for member in members)
        severities = [member.severity for member in members]

        return ComplaintPattern(
            topic=derive_pattern_topic(anchor_phrase, members),
            complaint_ids=[member.id for member in members],
            domain_code=domain_counts.most_common(1)[0][0],
            category_code=category_counts.most_common(1)[0][0],
            dominant_persona_code=persona_counts.most_common(1)[0][0],
            complaint_count=len(members),
            avg_severity=sum(severities) / len(severities),
        )
