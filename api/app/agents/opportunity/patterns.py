"""Deterministic recurring-topic detection from classified complaints."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from uuid import UUID

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

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _normalize_text(text: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(text.lower()))


def _extract_phrases(text: str, *, n: int) -> set[str]:
    tokens = [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOPWORDS]
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


class TopicPatternDetector:
    """Groups complaints by repeated multi-word phrases in summaries."""

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
            normalized = _normalize_text(complaint.summary)
            phrases = _extract_phrases(normalized, n=2) | _extract_phrases(normalized, n=3)
            for phrase in phrases:
                phrase_to_ids[phrase].add(complaint.id)

        eligible_phrases = [
            phrase
            for phrase, member_ids in phrase_to_ids.items()
            if len(member_ids) >= min_cluster_size
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
            for complaint_id in member_ids:
                assigned.add(complaint_id)

            patterns.append(self._build_pattern(phrase, members))

        return patterns

    @staticmethod
    def _build_pattern(topic: str, members: list[ComplaintEvidence]) -> ComplaintPattern:
        domain_counts = Counter(member.domain_code for member in members)
        category_counts = Counter(member.category_code for member in members)
        persona_counts = Counter(member.persona_code for member in members)
        severities = [member.severity for member in members]

        return ComplaintPattern(
            topic=topic.title(),
            complaint_ids=[member.id for member in members],
            domain_code=domain_counts.most_common(1)[0][0],
            category_code=category_counts.most_common(1)[0][0],
            dominant_persona_code=persona_counts.most_common(1)[0][0],
            complaint_count=len(members),
            avg_severity=sum(severities) / len(severities),
        )
