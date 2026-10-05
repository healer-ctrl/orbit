import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .tracer import (
    get_tracer,
    extract_traceparent,
    get_current_trace_id,
    get_current_span_id,
    get_current_traceparent,
)

logger = logging.getLogger("mailmind.http")


class TraceContextMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware for W3C Distributed Tracing and Structured Logging.
    - Extracts inbound W3C traceparent and tracestate headers.
    - Creates a server span per HTTP request.
    - Sets trace context on request.state for downstream controllers.
    - Injects traceparent & X-Trace-ID in HTTP response headers.
    - Records request duration, status code, and errors.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tracer = get_tracer()
        # Extract incoming context
        header_dict = dict(request.headers)
        parent_context = extract_traceparent(header_dict)

        span_name = f"HTTP {request.method} {request.url.path}"
        span = tracer.start_span(
            span_name,
            context=parent_context,
            kind=trace.SpanKind.SERVER,
        )

        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.route", request.url.path)
        span.set_attribute("http.client_ip", request.client.host if request.client else "unknown")

        start_time = time.time()

        with trace.use_span(span, end_on_exit=True):
            trace_id = get_current_trace_id()
            span_id = get_current_span_id()
            traceparent = get_current_traceparent()

            # Attach to request state for access in endpoints
            request.state.trace_id = trace_id
            request.state.span_id = span_id
            request.state.traceparent = traceparent

            try:
                response: Response = await call_next(request)
                duration_ms = int((time.time() - start_time) * 1000)

                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.duration_ms", duration_ms)

                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                else:
                    span.set_status(Status(StatusCode.OK))

                # Inject traceparent and X-Trace-ID in response headers
                response.headers["traceparent"] = traceparent
                response.headers["X-Trace-ID"] = trace_id
                response.headers["traceresponse"] = traceparent

                return response

            except Exception as exc:
                duration_ms = int((time.time() - start_time) * 1000)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute("http.duration_ms", duration_ms)
                logger.error(
                    "Unhandled exception during HTTP request processing: %s",
                    exc,
                    exc_info=True,
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "trace_id": trace_id,
                        "duration_ms": duration_ms,
                    },
                )
                raise
