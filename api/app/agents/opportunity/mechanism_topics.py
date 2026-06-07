"""Mechanism-primary topic labels for venture-aware pattern display."""

from __future__ import annotations



def format_signal_label(code: str) -> str:
    return " ".join(part.capitalize() for part in code.split("_"))


def format_founder_topic(
    *,
    business_function_code: str,
    jtbd_code: str | None,
    consequence_code: str | None,
) -> str:
    parts = [format_signal_label(business_function_code)]
    if jtbd_code is not None:
        parts.append(format_signal_label(jtbd_code))
    if consequence_code is not None:
        parts.append(format_signal_label(consequence_code))
    return " — ".join(parts[:3])


def format_mechanism_primary_topic(
    mechanism_fingerprint: str,
    consequence_code: str | None = None,
    *,
    verbatim_quote: str = "",
    summary: str = "",
) -> str:
    from app.agents.classification.signal_overlays import resolve_overlay_signals

    overlay = resolve_overlay_signals(
        mechanism_fingerprint,
        verbatim_quote=verbatim_quote,
        summary=summary,
    )
    if overlay is None:
        label = format_signal_label(mechanism_fingerprint.replace("_", " "))
        if consequence_code:
            return f"{label} — {format_signal_label(consequence_code)}"
        return label

    consequence = consequence_code or overlay.consequence_code
    return format_founder_topic(
        business_function_code=overlay.business_function_code,
        jtbd_code=overlay.jtbd_code,
        consequence_code=consequence,
    )
