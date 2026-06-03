"""Markdown generation and recommendation logic for executive reports."""

from __future__ import annotations

from datetime import UTC, datetime

from app.reports.executive.schemas import ExecutiveReportContent, TopOpportunityEntry

RECOMMEND_PRIORITIZE = "Prioritize — strong score and confidence; pursue validation."
RECOMMEND_EXPLORE = "Explore — worth founder validation conversations."
RECOMMEND_MONITOR = "Monitor — gather more complaint evidence before committing."
RECOMMEND_DEFER = "Defer — insufficient signal strength for now."


class ExecutiveReportGenerator:
    """Builds structured entries and markdown for the Top Opportunities report."""

    def __init__(self, *, key_complaints_limit: int = 5) -> None:
        self.key_complaints_limit = key_complaints_limit

    def recommend(self, *, score: int, confidence: float) -> str:
        if score >= 75 and confidence >= 0.7:
            return RECOMMEND_PRIORITIZE
        if score >= 55 and confidence >= 0.5:
            return RECOMMEND_EXPLORE
        if score >= 40:
            return RECOMMEND_MONITOR
        return RECOMMEND_DEFER

    def build_report(
        self,
        entries: list[TopOpportunityEntry],
        *,
        generated_at: datetime | None = None,
    ) -> ExecutiveReportContent:
        timestamp = generated_at or datetime.now(UTC)
        markdown = self.render_markdown(entries, generated_at=timestamp)
        return ExecutiveReportContent(
            markdown=markdown,
            opportunities=entries,
            generated_count=len(entries),
        )

    def render_markdown(
        self,
        entries: list[TopOpportunityEntry],
        *,
        generated_at: datetime,
    ) -> str:
        lines = [
            "# Top Opportunities Report",
            "",
            f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Opportunities ranked: {len(entries)}",
            "",
        ]

        if not entries:
            lines.append("_No scored opportunities available._")
            return "\n".join(lines)

        for index, entry in enumerate(entries, start=1):
            lines.extend(self._render_opportunity_section(index, entry))

        return "\n".join(lines)

    def _render_opportunity_section(self, rank: int, entry: TopOpportunityEntry) -> list[str]:
        lines = [
            f"## {rank}. {entry.title}",
            "",
            f"- **Score:** {entry.score}/100",
            f"- **Confidence:** {entry.confidence:.0%}",
            f"- **Recommendation:** {entry.recommendation}",
            f"- **Supporting evidence:** {entry.supporting_evidence_count} complaints",
            "",
            "### Problem",
            entry.problem_statement,
            "",
            "### Why recurring",
            entry.frequency_signal,
            "",
            "### Gap",
            entry.gap,
            "",
            "### Key complaints",
        ]

        if not entry.key_complaints:
            lines.append("_No linked complaints._")
        else:
            for complaint in entry.key_complaints:
                url_suffix = f" ([source]({complaint.source_url}))" if complaint.source_url else ""
                lines.append(
                    f"- **Severity {complaint.severity}/5** — {complaint.summary} "
                    f'"{complaint.verbatim_quote}"{url_suffix}'
                )

        lines.append("")
        return lines
