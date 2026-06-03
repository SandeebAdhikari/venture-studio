"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AI Venture Studio API"
    environment: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    api_key: str = Field(min_length=16, description="Shared API key for dashboard access")

    # Database — async URL used by the application runtime
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "avs"
    postgres_password: str = "avs"
    postgres_db: str = "ai_venture_studio"

    # Database pool
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_echo: bool = False

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = True

    # Future pipeline defaults (loaded now, used later)
    llm_daily_budget_usd: float = 2.0
    classify_batch_size: int = 50
    min_cluster_size: int = 3
    cluster_window_days: int = 30

    # LLM / classification
    openai_api_key: str = Field(default="", description="OpenAI API key for classification agent")
    classification_model: str = "gpt-4o-mini"
    classification_max_retries: int = 2
    classification_temperature: float = 0.0

    # LLM / opportunity generation
    generation_model: str = "gpt-4o-mini"
    generation_max_retries: int = 2
    generation_temperature: float = 0.2
    generation_batch_size: int = 500
    min_opportunity_confidence: float = 0.4
    min_avg_severity: float = 2.0

    # Opportunity scoring engine
    scoring_volume_target: int = 50

    # Executive reports
    executive_report_top_n: int = 10
    executive_report_key_complaints_limit: int = 5

    # Market research agent
    research_model: str = "gpt-4o-mini"
    research_max_retries: int = 2
    research_temperature: float = 0.3
    research_batch_size: int = 20

    # Competitor intelligence agent
    competitor_model: str = "gpt-4o-mini"
    competitor_max_retries: int = 2
    competitor_temperature: float = 0.3
    competitor_batch_size: int = 20

    # Customer research agent
    customer_research_model: str = "gpt-4o-mini"
    customer_research_max_retries: int = 2
    customer_research_temperature: float = 0.2
    customer_research_batch_size: int = 20

    # Revenue validation agent
    revenue_validation_model: str = "gpt-4o-mini"
    revenue_validation_max_retries: int = 2
    revenue_validation_temperature: float = 0.2
    revenue_validation_batch_size: int = 20

    # Product strategy agent
    product_strategy_model: str = "gpt-4o-mini"
    product_strategy_max_retries: int = 2
    product_strategy_temperature: float = 0.2
    product_strategy_batch_size: int = 20

    # Go-to-market agent
    go_to_market_model: str = "gpt-4o-mini"
    go_to_market_max_retries: int = 2
    go_to_market_temperature: float = 0.2
    go_to_market_batch_size: int = 20

    # Growth strategy agent
    growth_strategy_model: str = "gpt-4o-mini"
    growth_strategy_max_retries: int = 2
    growth_strategy_temperature: float = 0.2
    growth_strategy_batch_size: int = 20

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy connection URL (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Sync SQLAlchemy connection URL for Alembic migrations."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — safe to call on every request."""
    return Settings()
