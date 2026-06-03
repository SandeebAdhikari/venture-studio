"""Text normalization pipeline for raw complaint ingestion."""

import hashlib
import re
import unicodedata

from app.collection.schemas import NormalizedComplaint

_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\ufeff]")
_WHITESPACE_RE = re.compile(r"\s+")
_URL_ONLY_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


class TextNormalizer:
    """Deterministic normalization for reliable deduplication and storage."""

    def __init__(self, version: str = "1.0.0") -> None:
        self.version = version

    def normalize(self, *, title: str | None, body: str) -> NormalizedComplaint:
        normalized_title = self._normalize_optional_text(title)
        normalized_body = self._normalize_required_text(body)
        combined = self._combine(normalized_title, normalized_body)
        content_hash = self.compute_hash(combined)
        return NormalizedComplaint(
            title=normalized_title,
            body=normalized_body,
            combined_text=combined,
            content_hash=content_hash,
            normalizer_version=self.version,
        )

    def compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def is_url_only(self, text: str) -> bool:
        return bool(_URL_ONLY_RE.match(text.strip()))

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = self._normalize_required_text(value)
        return normalized or None

    def _normalize_required_text(self, value: str) -> str:
        text = unicodedata.normalize("NFC", value)
        text = _ZERO_WIDTH_RE.sub("", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = _WHITESPACE_RE.sub(" ", text)
        return text.strip()

    def _combine(self, title: str | None, body: str) -> str:
        if title:
            return f"{title}\n\n{body}".strip()
        return body
