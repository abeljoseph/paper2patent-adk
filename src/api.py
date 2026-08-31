"""FastAPI REST API Server for Paper2Patent ADK Multi-Agent Service."""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.config import settings
from src.agents.coordinator import Paper2PatentCoordinator, PipelineExecutionResult
from src.observability.tracer import global_tracer
from src.observability.metrics import global_metrics

app = FastAPI(
    title="Paper2Patent ADK API",
    description="REST API for autonomous academic research paper to patent claim drafting with Google ADK.",
    version="1.0.0",
)

coordinator = Paper2PatentCoordinator()


class AnalyzeRequest(BaseModel):
    """Request payload to process research paper."""
    paper_text: str = Field(..., description="Raw text of the academic paper or arXiv manuscript.", min_length=20)
    session_id: Optional[str] = Field(None, description="Optional session tracking ID.")
    max_refinement_cycles: int = Field(default=1, ge=0, le=3)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    model: str
    adk_framework: str = "Google ADK (Python)"


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Service health probe."""
    return HealthResponse(
        status="HEALTHY",
        version="1.0.0",
        model=settings.MODEL_NAME,
    )


@app.post("/api/v1/analyze", response_model=PipelineExecutionResult)
def analyze_paper(request: AnalyzeRequest):
    """Execute complete ADK multi-agent pipeline on research paper text."""
    try:
        result = coordinator.run_pipeline(
            paper_text=request.paper_text,
            session_id=request.session_id,
            max_refinement_cycles=request.max_refinement_cycles,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/traces/{trace_id}")
def get_trace_logs(trace_id: str):
    """Fetch OpenTelemetry spans and telemetry metrics for a trace ID."""
    spans = global_tracer.get_traces_for_id(trace_id)
    if not spans:
        raise HTTPException(status_code=404, detail="Trace ID not found.")
    metrics = global_metrics.compute_trace_metrics(spans)
    return {
        "trace_id": trace_id,
        "metrics": metrics,
        "spans": [s.model_dump() for s in spans],
    }
