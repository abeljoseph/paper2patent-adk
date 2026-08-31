"""Agent Tracing utilizing official OpenTelemetry SDK and active PII scrubbing."""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

# OpenTelemetry SDK imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource

from src.observability.pii_scrubber import PIIScrubber

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Paper2Patent.Tracer")


class InMemorySpanExporter(SpanExporter):
    """In-memory exporter for OpenTelemetry spans."""

    def __init__(self):
        self._spans: List[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self) -> List[ReadableSpan]:
        return list(self._spans)

    def clear(self):
        self._spans.clear()

    def shutdown(self):
        self.clear()


class AgentTraceSpan(BaseModel):
    """Structured span representing an agent execution or tool call."""
    
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str
    parent_span_id: Optional[str] = None
    step_name: str
    agent_name: str
    component_type: str = "agent"  # agent, tool, memory, coordinator
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    status: str = "RUNNING"  # RUNNING, SUCCESS, ERROR, RECOVERED
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    error_message: Optional[str] = None

    def finish(self, status: str = "SUCCESS", outputs: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Mark span as finished, scrub data, and calculate duration."""
        self.end_time = datetime.now(timezone.utc).isoformat()
        self.status = status
        if outputs:
            self.outputs = PIIScrubber.scrub_data(outputs)
        if error:
            self.error_message = PIIScrubber.scrub_text(error)
        
        # Calculate duration
        start_dt = datetime.fromisoformat(self.start_time)
        end_dt = datetime.fromisoformat(self.end_time)
        self.duration_ms = round((end_dt - start_dt).total_seconds() * 1000, 2)


class AgentTracer:
    """Central Tracer backed by official OpenTelemetry SDK and JSON Lines persistence."""

    def __init__(self, log_path: str = "logs/traces.jsonl"):
        self.log_path = log_path
        self.spans: List[AgentTraceSpan] = []
        self._ensure_log_dir()
        self._init_opentelemetry()

    def _ensure_log_dir(self):
        os.makedirs(os.path.dirname(self.log_path) if os.path.dirname(self.log_path) else ".", exist_ok=True)

    def _init_opentelemetry(self):
        """Initialize OpenTelemetry SDK TracerProvider and In-Memory exporter."""
        resource = Resource.create(attributes={"service.name": "paper2patent-adk-agent"})
        self.otel_provider = TracerProvider(resource=resource)
        self.otel_exporter = InMemorySpanExporter()
        self.otel_provider.add_span_processor(SimpleSpanProcessor(self.otel_exporter))
        trace.set_tracer_provider(self.otel_provider)
        self.otel_tracer = trace.get_tracer("paper2patent.adk")

    def start_span(
        self,
        trace_id: str,
        step_name: str,
        agent_name: str,
        component_type: str = "agent",
        inputs: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None,
    ) -> AgentTraceSpan:
        """Start a new trace span with active PII scrubbing."""
        cleaned_inputs = PIIScrubber.scrub_data(inputs or {})
        span = AgentTraceSpan(
            trace_id=trace_id,
            step_name=step_name,
            agent_name=agent_name,
            component_type=component_type,
            inputs=cleaned_inputs,
            parent_span_id=parent_span_id,
        )
        self.spans.append(span)

        # Also emit to OpenTelemetry SDK tracer
        with self.otel_tracer.start_as_current_span(f"{agent_name}.{step_name}") as otel_span:
            otel_span.set_attribute("agent.name", agent_name)
            otel_span.set_attribute("agent.component", component_type)
            otel_span.set_attribute("trace.id", trace_id)

        logger.info(f"[{trace_id}] STARTED: {agent_name} -> {step_name}")
        return span

    def end_span(
        self,
        span: AgentTraceSpan,
        status: str = "SUCCESS",
        outputs: Optional[Dict[str, Any]] = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        error: Optional[str] = None,
    ):
        """End, scrub, and persist span."""
        span.tokens_in = tokens_in
        span.tokens_out = tokens_out
        span.finish(status=status, outputs=outputs, error=error)
        self._persist_span(span)
        logger.info(
            f"[{span.trace_id}] {status}: {span.agent_name} -> {span.step_name} ({span.duration_ms}ms, {tokens_in + tokens_out} tokens)"
        )

    def _persist_span(self, span: AgentTraceSpan):
        """Append span to JSON Lines log file."""
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(span.model_dump_json() + "\n")
        except Exception as e:
            logger.warning(f"Could not persist trace span: {e}")

    def get_traces_for_id(self, trace_id: str) -> List[AgentTraceSpan]:
        """Fetch all spans belonging to a trace."""
        return [s for s in self.spans if s.trace_id == trace_id]

    def clear(self):
        """Clear memory trace list."""
        self.spans.clear()
        self.otel_exporter.clear()


# Global tracer singleton
global_tracer = AgentTracer()


def trace_agent_step(agent_name: str, step_name: Optional[str] = None, component_type: str = "agent"):
    """Decorator to trace agent methods and tool calls automatically."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            actual_step_name = step_name or func.__name__
            trace_id = kwargs.get("trace_id")
            if not trace_id and args and hasattr(args[0], "trace_id"):
                trace_id = getattr(args[0], "trace_id")
            if not trace_id:
                trace_id = str(uuid.uuid4())[:8]

            safe_inputs = PIIScrubber.scrub_data({
                k: str(v)[:200] for k, v in kwargs.items()
            })
            span = global_tracer.start_span(
                trace_id=trace_id,
                step_name=actual_step_name,
                agent_name=agent_name,
                component_type=component_type,
                inputs=safe_inputs,
            )
            
            try:
                result = func(*args, **kwargs)
                safe_output = PIIScrubber.scrub_data({"summary": str(result)[:300]})
                tok_in = len(str(safe_inputs)) // 4
                tok_out = len(str(result)) // 4
                global_tracer.end_span(
                    span, status="SUCCESS", outputs=safe_output, tokens_in=tok_in, tokens_out=tok_out
                )
                return result
            except Exception as ex:
                global_tracer.end_span(
                    span, status="ERROR", error=str(ex)
                )
                raise ex

        return wrapper
    return decorator
