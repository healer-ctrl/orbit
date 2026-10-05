import os
import contextlib
import time
from typing import Dict, Optional, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.context import Context

_tracer_initialized = False
_TRACER_NAME = "mailmind"


def init_tracer(
    service_name: str = "mailmind-backend",
    service_version: str = "1.0.0",
    enable_console_exporter: bool = False,
) -> trace.Tracer:
    """
    Initializes the OpenTelemetry TracerProvider with standardized W3C TraceContext propagation.
    """
    global _tracer_initialized
    if _tracer_initialized:
        return trace.get_tracer(_TRACER_NAME)

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
            "cloud.provider": "azure",
        }
    )

    provider = TracerProvider(resource=resource)
    if enable_console_exporter:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer_initialized = True
    return trace.get_tracer(_TRACER_NAME)


def get_tracer(name: Optional[str] = None) -> trace.Tracer:
    """Returns the OpenTelemetry tracer instance."""
    if not _tracer_initialized:
        init_tracer()
    return trace.get_tracer(name or _TRACER_NAME)


def get_current_trace_id() -> str:
    """Returns the active 32-hex trace ID or a fallback 0-filled string."""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return "0" * 32


def get_current_span_id() -> str:
    """Returns the active 16-hex span ID or a fallback 0-filled string."""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return "0" * 16


def get_current_traceparent() -> str:
    """
    Returns W3C traceparent string: 00-{trace_id}-{span_id}-{trace_flags}
    Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        ctx = span.get_span_context()
        trace_id = format(ctx.trace_id, "032x")
        span_id = format(ctx.span_id, "016x")
        flags = format(ctx.trace_flags, "02x")
        return f"00-{trace_id}-{span_id}-{flags}"
    return "00-00000000000000000000000000000000-0000000000000000-01"


def inject_traceparent(carrier: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Injects W3C traceparent and tracestate headers into the carrier dict for outbound requests.
    """
    if carrier is None:
        carrier = {}
    TraceContextTextMapPropagator().inject(carrier)
    # Ensure standard traceparent is always explicitly present
    tp = get_current_traceparent()
    carrier["traceparent"] = tp
    carrier["X-Trace-ID"] = get_current_trace_id()
    return carrier


def extract_traceparent(carrier: Dict[str, Any]) -> Context:
    """
    Extracts W3C traceparent context from an incoming carrier / headers dictionary.
    """
    # Normalize headers to lowercase string dict
    normalized = {str(k).lower(): str(v) for k, v in carrier.items()}
    return TraceContextTextMapPropagator().extract(carrier=normalized)


@contextlib.contextmanager
def trace_agent_step(
    agent_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_context: Optional[Context] = None,
):
    """
    Context manager to trace multi-agent operations with W3C propagation,
    recording start/end metrics, custom attributes, and handling exceptions cleanly.
    """
    tracer = get_tracer()
    span_name = f"agent.{agent_name}"
    span = tracer.start_span(span_name, context=parent_context)
    span.set_attribute("agent.name", agent_name)

    if attributes:
        for k, v in attributes.items():
            if v is not None:
                if isinstance(v, (str, bool, int, float)):
                    span.set_attribute(f"agent.{k}", v)
                else:
                    span.set_attribute(f"agent.{k}", str(v))

    start_time = time.time()
    try:
        with trace.use_span(span, end_on_exit=True):
            yield span
            span.set_status(Status(StatusCode.OK))
    except Exception as exc:
        span.record_exception(exc)
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        raise
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        span.set_attribute("agent.duration_ms", duration_ms)
