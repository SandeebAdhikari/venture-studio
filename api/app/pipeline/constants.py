"""Pipeline orchestration constants."""

from app.db.enums import PipelineStage

# Canonical ordered execution sequence for the full Venture Studio pipeline.
PIPELINE_STAGE_ORDER: tuple[PipelineStage, ...] = (
    PipelineStage.COLLECT,
    PipelineStage.CLASSIFY,
    PipelineStage.GENERATE_OPPORTUNITIES,
    PipelineStage.SCORE_OPPORTUNITIES,
    PipelineStage.MARKET_RESEARCH,
    PipelineStage.COMPETITOR_ANALYSIS,
    PipelineStage.CUSTOMER_RESEARCH,
    PipelineStage.REVENUE_VALIDATION,
    PipelineStage.PRODUCT_STRATEGY,
    PipelineStage.GO_TO_MARKET,
    PipelineStage.GROWTH_STRATEGY,
    PipelineStage.HUMAN_PROXY,
    PipelineStage.EXECUTIVE_RANKING,
    PipelineStage.VENTURE_REPORT,
)

# Public alias matching the product term "pipeline state".
PipelineState = PipelineStage

PIPELINE_LOCK_KEY = "lock:pipeline:run"
