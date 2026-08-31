"""Metrics collector for agent latency, token usage, and execution telemetry."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class ExecutionMetrics(BaseModel):
    """Aggregated execution metrics for an agent run."""
    trace_id: str
    total_duration_ms: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_tokens: int = 0
    steps_count: int = 0
    agent_breakdown: Dict[str, float] = Field(default_factory=dict)
    tool_invocations: Dict[str, int] = Field(default_factory=dict)


class MetricsCollector:
    """Collects and computes metrics across agent runs."""

    @staticmethod
    def compute_trace_metrics(spans: List[Any]) -> ExecutionMetrics:
        """Compute metrics from a list of AgentTraceSpan objects."""
        if not spans:
            return ExecutionMetrics(trace_id="unknown")
        
        trace_id = spans[0].trace_id
        total_duration = 0.0
        tokens_in = 0
        tokens_out = 0
        agent_breakdown: Dict[str, float] = {}
        tool_counts: Dict[str, int] = {}

        for span in spans:
            total_duration += span.duration_ms
            tokens_in += span.tokens_in
            tokens_out += span.tokens_out
            
            # Agent breakdown
            agent_breakdown[span.agent_name] = round(
                agent_breakdown.get(span.agent_name, 0.0) + span.duration_ms, 2
            )
            
            # Tool counts
            if span.component_type == "tool":
                tool_counts[span.step_name] = tool_counts.get(span.step_name, 0) + 1

        return ExecutionMetrics(
            trace_id=trace_id,
            total_duration_ms=round(total_duration, 2),
            total_tokens_in=tokens_in,
            total_tokens_out=tokens_out,
            total_tokens=tokens_in + tokens_out,
            steps_count=len(spans),
            agent_breakdown=agent_breakdown,
            tool_invocations=tool_counts,
        )


global_metrics = MetricsCollector()
