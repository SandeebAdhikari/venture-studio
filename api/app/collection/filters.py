"""Pre-insert validation filters for collection."""

from app.collection.schemas import NormalizedComplaint
from app.collection.settings import CollectionSettings


class CollectionFilter:
    """Reject items that should not be stored before classification."""

    def __init__(self, settings: CollectionSettings | None = None) -> None:
        self._settings = settings or CollectionSettings()

    def rejection_reason(self, normalized: NormalizedComplaint, *, url: str) -> str | None:
        if self._is_url_only(normalized.body) and not normalized.title:
            return "url_only_body"

        if self._is_url_only(normalized.combined_text):
            return "url_only_content"

        if len(normalized.combined_text) < self._settings.min_text_length:
            return f"text_too_short: minimum {self._settings.min_text_length} characters required"

        return None

    @staticmethod
    def _is_url_only(text: str) -> bool:
        stripped = text.strip()
        return stripped.startswith(("http://", "https://")) and " " not in stripped
