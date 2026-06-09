"""Resolve dominant mechanism fingerprint from opportunity complaints (FF-CM-5)."""

from __future__ import annotations

from collections import Counter

from app.agents.opportunity.mechanism_fingerprints import extract_mechanism_fingerprint
from app.db.models.complaint import Complaint


def resolve_dominant_mechanism_fingerprint(complaints: list[Complaint]) -> str | None:
    """Return the mode mechanism fingerprint across linked complaints."""
    if not complaints:
        return None

    fingerprints: list[str] = []
    for complaint in complaints:
        fingerprint = extract_mechanism_fingerprint(
            verbatim_quote=complaint.verbatim_quote or "",
            summary=complaint.summary or "",
        )
        if fingerprint is not None:
            fingerprints.append(fingerprint)

    if not fingerprints:
        return None

    return Counter(fingerprints).most_common(1)[0][0]
