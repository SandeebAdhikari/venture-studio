"""HTTP middleware for request tracing and metrics."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from app.observability.metrics import record_metrics
from app.observability.tracing import set_trace_id, trace_span


def _resolve_path_template(request: Request) -> str:
    for route in request.app.routes:
        match, _scope = route.matches(request.scope)
        if match == Match.FULL and hasattr(route, "path"):
            return route.path
    return request.url.path


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach trace IDs, record HTTP metrics, and emit request spans."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
        set_trace_id(trace_id)
        path_template = _resolve_path_template(request)
        started = time.perf_counter()

        with trace_span(
            "http.request",
            attributes={
                "http.method": request.method,
                "http.route": path_template,
                "http.target": request.url.path,
            },
            trace_id=trace_id,
        ):
            response = await call_next(request)

        duration_sec = time.perf_counter() - started
        record_metrics().record_http_request(
            method=request.method,
            path_template=path_template,
            status_code=response.status_code,
            duration_sec=duration_sec,
        )
        response.headers["X-Trace-Id"] = trace_id
        return response
