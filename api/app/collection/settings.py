"""Collection configuration defaults."""

from pydantic import Field
from pydantic_settings import BaseSettings


class CollectionSettings(BaseSettings):
    """Settings for the complaint/signal collection pipeline."""

    min_text_length: int = Field(default=50, ge=1, description="Min combined title+body length")
    dedup_by_url: bool = Field(default=True, description="Reject duplicate canonical URLs globally")
    dedup_by_content_hash: bool = Field(
        default=True,
        description="Reject duplicate normalized content within a source",
    )
    normalizer_version: str = Field(default="1.0.0")
