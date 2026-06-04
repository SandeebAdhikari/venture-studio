"""Readable markdown formatting for structured agent JSON in venture reports."""

from __future__ import annotations

from typing import Any


def normalize_century_score(value: int | float | None) -> int | None:
    """Map agent scores that used a 0–10 scale into 0–100 for display."""
    if value is None:
        return None
    numeric = float(value)
    if 0 <= numeric <= 10:
        return int(round(numeric * 10))
    return int(round(numeric))


def format_score_display(value: int | float | None, *, suffix: str = "/100") -> str:
    normalized = normalize_century_score(value)
    if normalized is None:
        return "N/A"
    return f"{normalized}{suffix}"


def format_differentiation_score(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if 0 <= numeric <= 1:
        return f"{int(round(numeric * 100))}/100"
    return f"{int(round(numeric))}/100"


def format_structured_bullet(item: Any) -> str:
    """Turn JSON objects from agent outputs into founder-readable bullets."""
    if item is None:
        return "—"
    if isinstance(item, str):
        return item.strip() or "—"
    if not isinstance(item, dict):
        return str(item).strip()

    if "phase_name" in item or "phase_number" in item:
        return format_roadmap_phase(item)
    if "persona_name" in item or ("role" in item and "pain_points" in item):
        return format_persona(item)
    if "channel_name" in item or ("channel_type" in item and "priority" in item):
        return format_acquisition_channel(item)
    if "focus" in item and ("duration_months" in item or "end_month" in item):
        return format_growth_phase(item)
    if "gap" in item or "description" in item:
        return format_competitive_gap(item)
    if "name" in item and "segment" not in item:
        return str(item.get("name"))
    if "segment" in item:
        return str(item.get("segment") or item.get("name") or item)
    if "trend" in item or "title" in item:
        return str(item.get("trend") or item.get("title") or item)
    if "feature" in item or "name" in item:
        return str(item.get("name") or item.get("feature") or item)

    label = (
        item.get("title")
        or item.get("milestone")
        or item.get("phase")
        or item.get("channel")
        or item.get("persona")
    )
    if label:
        return str(label)
    return format_key_value_summary(item)


def format_roadmap_phase(phase: dict[str, Any]) -> str:
    name = phase.get("phase_name") or f"Phase {phase.get('phase_number', '?')}"
    start = phase.get("start_week")
    end = phase.get("end_week")
    weeks = phase.get("duration_weeks")
    window = ""
    if start is not None and end is not None:
        window = f" (weeks {start}–{end})"
    elif weeks is not None:
        window = f" ({weeks} weeks)"

    parts = [f"**{name}**{window}"]
    milestones = phase.get("milestones") or []
    if milestones:
        parts.append(f"Milestones: {', '.join(str(m) for m in milestones[:4])}")
    deliverables = phase.get("deliverables") or []
    if deliverables:
        parts.append(f"Deliverables: {', '.join(str(d) for d in deliverables[:4])}")
    return " — ".join(parts)


def format_persona(persona: dict[str, Any]) -> str:
    name = persona.get("persona_name") or persona.get("name") or "Persona"
    role = persona.get("role")
    header = f"**{name}**"
    if role:
        header = f"{header} ({role})"

    pains = persona.get("pain_points") or []
    goals = persona.get("goals") or []
    channels = persona.get("preferred_channels") or []
    segments = []
    if pains:
        segments.append(f"pain: {', '.join(str(p) for p in pains[:3])}")
    if goals:
        segments.append(f"goals: {', '.join(str(g) for g in goals[:3])}")
    if channels:
        segments.append(f"channels: {', '.join(str(c) for c in channels[:3])}")
    if segments:
        return f"{header} — {'; '.join(segments)}"
    return header


def format_acquisition_channel(channel: dict[str, Any]) -> str:
    name = channel.get("channel_name") or channel.get("name") or channel.get("channel") or "Channel"
    priority = channel.get("priority")
    channel_type = channel.get("channel_type")
    cac = channel.get("estimated_cac_usd")
    rationale = channel.get("rationale")

    meta = []
    if priority:
        meta.append(str(priority))
    if channel_type:
        meta.append(str(channel_type))
    if cac is not None:
        meta.append(f"est. CAC ${float(cac):,.0f}")

    line = f"**{name}**"
    if meta:
        line = f"{line} ({', '.join(meta)})"
    if rationale:
        line = f"{line}: {rationale}"
    return line


def format_growth_phase(phase: dict[str, Any]) -> str:
    name = phase.get("phase_name") or "Growth phase"
    start = phase.get("start_month")
    end = phase.get("end_month")
    months = phase.get("duration_months")
    window = ""
    if start is not None and end is not None:
        window = f" (months {start}–{end})"
    elif months is not None:
        window = f" ({months} months)"

    focus = phase.get("focus")
    levers = phase.get("growth_levers") or []
    milestones = phase.get("milestones") or []

    parts = [f"**{name}**{window}"]
    if focus:
        parts.append(str(focus))
    if levers:
        parts.append(f"Levers: {', '.join(str(lever) for lever in levers[:4])}")
    if milestones:
        parts.append(f"Milestones: {', '.join(str(m) for m in milestones[:3])}")
    return " — ".join(parts)


def format_competitive_gap(gap: dict[str, Any]) -> str:
    title = gap.get("gap") or gap.get("title") or gap.get("name") or "Gap"
    detail = gap.get("description") or gap.get("rationale")
    if detail and str(detail) != str(title):
        return f"**{title}** — {detail}"
    return f"**{title}**"


def format_competitor_profile(
    *,
    name: str,
    positioning: str,
    sentiment_score: float,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
) -> str:
    lines = [f"**{name}** — {positioning} (sentiment {sentiment_score:+.2f})"]
    if strengths:
        lines.append(f"  - Strengths: {', '.join(strengths[:3])}")
    if weaknesses:
        lines.append(f"  - Weaknesses: {', '.join(weaknesses[:3])}")
    return "\n".join(lines)


def format_key_value_summary(data: dict[str, Any], *, max_keys: int = 4) -> str:
    pairs = []
    for key, value in list(data.items())[:max_keys]:
        if key in {"id", "created_at", "updated_at"}:
            continue
        if isinstance(value, (list, dict)):
            continue
        pairs.append(f"{key.replace('_', ' ')}: {value}")
    return "; ".join(pairs) if pairs else str(data)


def format_bullet_list(items: list[Any], *, empty: str = "_No data available._") -> str:
    if not items:
        return empty
    return "\n".join(f"- {format_structured_bullet(item)}" for item in items)


def market_size_disclaimer(*, has_evidence: bool) -> str:
    if has_evidence:
        return (
            "_TAM/SAM figures are model estimates from agent research. "
            "See supporting evidence below — validate with primary sources before planning._"
        )
    return (
        "_TAM/SAM figures are unaudited model estimates with no linked citations. "
        "Treat as directional only and validate with primary research._"
    )
