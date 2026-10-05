import json
import logging
from unittest.mock import MagicMock
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from backend.telemetry import (
    init_tracer,
    get_tracer,
    get_current_trace_id,
    get_current_span_id,
    get_current_traceparent,
    inject_traceparent,
    extract_traceparent,
    trace_agent_step,
    StructuredJsonFormatter,
)


def test_init_tracer_and_span_creation():
    tracer = init_tracer(service_name="mailmind-test-backend")
    assert tracer is not None

    with tracer.start_as_current_span("test_span") as span:
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        tp = get_current_traceparent()

        assert len(trace_id) == 32
        assert len(span_id) == 16
        assert tp.startswith("00-")
        assert trace_id in tp
        assert span_id in tp


def test_traceparent_injection_and_extraction():
    tracer = get_tracer()
    with tracer.start_as_current_span("parent_span"):
        headers = {}
        inject_traceparent(headers)

        assert "traceparent" in headers
        assert "X-Trace-ID" in headers
        tp = headers["traceparent"]
        assert tp.startswith("00-")

        # Extract in downstream context
        extracted_ctx = extract_traceparent(headers)
        assert extracted_ctx is not None


def test_trace_agent_step_decorator():
    with trace_agent_step("TestClassifierAgent", {"step_num": 1, "test_key": "val"}) as span:
        trace_id = get_current_trace_id()
        assert len(trace_id) == 32
        tp = get_current_traceparent()
        assert tp.startswith("00-")

    # Verify exception recording in agent step
    try:
        with trace_agent_step("FailingAgent", {"status": "error"}):
            raise ValueError("Deliberate test error")
    except ValueError:
        pass


def test_structured_json_formatter():
    formatter = StructuredJsonFormatter(service_name="mailmind-backend", environment="test")
    record = logging.LogRecord(
        name="mailmind.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test financial operations log message",
        args=(),
        exc_info=None,
    )
    record.email_id = "EML-1001"
    record.intent = "CORPORATE_ACTION"

    formatted_str = formatter.format(record)
    parsed = json.loads(formatted_str)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "mailmind.test"
    assert parsed["message"] == "Test financial operations log message"
    assert parsed["service"] == "mailmind-backend"
    assert parsed["environment"] == "test"
    assert "timestamp" in parsed
    assert "trace_id" in parsed
    assert "span_id" in parsed
    assert "traceparent" in parsed
    assert parsed["context"]["email_id"] == "EML-1001"
    assert parsed["context"]["intent"] == "CORPORATE_ACTION"
