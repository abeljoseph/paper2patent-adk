"""Unit tests for Observability, OpenTelemetry Tracing, and Telemetry Metrics."""

import pytest
from src.observability.tracer import AgentTracer, AgentTraceSpan
from src.observability.metrics import MetricsCollector


def test_tracer_lifecycle(tmp_path):
    log_file = str(tmp_path / "test_traces.jsonl")
    tracer = AgentTracer(log_path=log_file)

    trace_id = "test-trace-001"
    span = tracer.start_span(
        trace_id=trace_id,
        step_name="test_step",
        agent_name="TestAgent",
        component_type="agent",
        inputs={"param": "value"},
    )

    assert span.status == "RUNNING"
    assert span.trace_id == trace_id

    tracer.end_span(span, status="SUCCESS", outputs={"out": 123}, tokens_in=50, tokens_out=100)

    assert span.status == "SUCCESS"
    assert span.tokens_in == 50
    assert span.tokens_out == 100
    assert span.duration_ms >= 0.0

    retrieved = tracer.get_traces_for_id(trace_id)
    assert len(retrieved) == 1
    assert retrieved[0].step_name == "test_step"


def test_metrics_computation():
    span1 = AgentTraceSpan(
        trace_id="tr-1",
        step_name="step1",
        agent_name="AgentA",
        tokens_in=100,
        tokens_out=50,
        duration_ms=120.0,
    )
    span2 = AgentTraceSpan(
        trace_id="tr-1",
        step_name="step2",
        agent_name="AgentB",
        tokens_in=200,
        tokens_out=150,
        duration_ms=180.0,
    )

    metrics = MetricsCollector.compute_trace_metrics([span1, span2])
    assert metrics.trace_id == "tr-1"
    assert metrics.total_tokens == 500
    assert metrics.total_duration_ms == 300.0
    assert metrics.steps_count == 2
    assert "AgentA" in metrics.agent_breakdown
    assert "AgentB" in metrics.agent_breakdown
