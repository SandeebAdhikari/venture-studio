"""ARQ worker settings and Redis connection configuration."""

from arq.connections import RedisSettings
from arq.worker import func as arq_func

from app.config import get_settings
from app.workers.context import worker_shutdown, worker_startup
from app.workers.jobs import (
    classify,
    collect,
    competitor_analysis,
    customer_research,
    executive_ranking,
    generate_opportunities,
    go_to_market,
    growth_strategy,
    human_proxy,
    market_research,
    product_strategy,
    revenue_validation,
    run_pipeline,
    score,
    venture_report,
)


def get_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
        password=settings.redis_password,
    )


def _job(func, *, name: str | None = None):
    settings = get_settings()
    return arq_func(
        func,
        name=name,
        max_tries=settings.arq_max_tries,
        timeout=settings.arq_job_timeout_sec,
        keep_result=settings.arq_job_result_ttl_sec,
    )


class WorkerSettings:
    """Entry point for `arq app.workers.worker.WorkerSettings`."""

    functions = [
        _job(collect),
        _job(classify),
        _job(generate_opportunities),
        _job(score),
        _job(market_research),
        _job(competitor_analysis),
        _job(customer_research),
        _job(revenue_validation),
        _job(product_strategy),
        _job(go_to_market),
        _job(growth_strategy),
        _job(human_proxy),
        _job(executive_ranking),
        _job(venture_report),
        _job(run_pipeline),
    ]
    on_startup = worker_startup
    on_shutdown = worker_shutdown
    redis_settings = get_redis_settings()
    max_jobs = get_settings().arq_max_jobs
    job_timeout = get_settings().arq_job_timeout_sec
    keep_result = get_settings().arq_job_result_ttl_sec
    queue_name = get_settings().arq_queue_name
