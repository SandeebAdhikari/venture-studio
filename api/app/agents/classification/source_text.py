"""Normalize signal text for verbatim-quote grounding checks."""

from __future__ import annotations

import html
import re
import unicodedata
from html.parser import HTMLParser

_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\ufeff]")
_WHITESPACE_RE = re.compile(r"\s+")
_TAG_FALLBACK_RE = re.compile(r"<[^>]+>")


class _HTMLTextExtractor(HTMLParser):
    """Collect visible text; preserve entity references for a later unescape pass."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._parts.append(f"&#{name};")

    def text(self) -> str:
        return "".join(self._parts)


def unescape_html_entities(text: str, *, max_rounds: int = 3) -> str:
    current = text
    for _ in range(max_rounds):
        decoded = html.unescape(current)
        if decoded == current:
            break
        current = decoded
    return current


def strip_html_tags(text: str) -> str:
    if "<" not in text and "&lt;" not in text.lower():
        return text
    parser = _HTMLTextExtractor()
    try:
        parser.feed(text)
        parser.close()
        return parser.text()
    except Exception:
        return _TAG_FALLBACK_RE.sub(" ", text)


def normalize_for_verbatim_grounding(text: str) -> str:
    """Decode entities, remove markup, and collapse whitespace for substring checks."""
    normalized = unicodedata.normalize("NFC", text)
    normalized = _ZERO_WIDTH_RE.sub("", normalized)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = unescape_html_entities(normalized)
    normalized = strip_html_tags(normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def build_classification_source_text(*, title: str | None, body: str) -> str:
    if title:
        raw = f"{title}\n\n{body}"
    else:
        raw = body
    return normalize_for_verbatim_grounding(raw)


def verbatim_quote_in_source(*, quote: str, source_text: str) -> bool:
    """Return True when quote is a grounded substring of source (case-insensitive fallback)."""
    normalized_quote = normalize_for_verbatim_grounding(quote)
    if not normalized_quote:
        return False

    normalized_source = normalize_for_verbatim_grounding(source_text)
    if normalized_quote in normalized_source:
        return True
    return normalized_quote.lower() in normalized_source.lower()
