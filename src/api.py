"""FastAPI REST API Server for Paper2Patent ADK Multi-Agent Service with Async & HITL."""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.config import settings
from src.agents.coordinator import Paper2PatentCoordinator, PipelineExecutionResult
from src.eval.benchmark import GoldenDatasetEvaluator, EvaluationMetricSummary
from src.observability.tracer import global_tracer
from src.observability.metrics import global_metrics

app = FastAPI(
    title="Paper2Patent ADK API",
    description="REST API for autonomous academic research paper to patent claim drafting with Google ADK, Model Routing, and HITL.",
    version="1.0.0",
)

coordinator = Paper2PatentCoordinator()


class AnalyzeRequest(BaseModel):
    """Request payload to process research paper."""
    paper_text: str = Field(..., description="Raw text of the academic paper or arXiv manuscript.", min_length=20)
    session_id: Optional[str] = Field(None, description="Optional session tracking ID.")
    require_human_approval: bool = Field(default=False, description="Whether to pause after Stage 2 for Human-in-the-Loop review.")
    max_refinement_cycles: int = Field(default=1, ge=0, le=3)


class ApprovalRequest(BaseModel):
    """Payload to resume a paused pipeline after human attorney approval."""
    human_approved: bool = Field(default=True, description="Approval decision.")
    human_feedback: Optional[str] = Field(None, description="Optional attorney feedback or claim adjustments.")
    max_refinement_cycles: int = Field(default=1, ge=0, le=3)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    model: str
    adk_framework: str = "Google ADK (Python)"
    storage: str = "SQLite Persistent Database"
    observability: str = "OpenTelemetry SDK + PII Scrubber"


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Service health probe."""
    return HealthResponse(
        status="HEALTHY",
        version="1.0.0",
        model=settings.MODEL_NAME,
    )


@app.post("/api/v1/analyze", response_model=PipelineExecutionResult)
async def analyze_paper(request: AnalyzeRequest):
    """Execute complete ADK multi-agent pipeline on research paper text asynchronously."""
    try:
        result = await coordinator.run_pipeline_async(
            paper_text=request.paper_text,
            session_id=request.session_id,
            require_human_approval=request.require_human_approval,
            max_refinement_cycles=request.max_refinement_cycles,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/pipeline/{session_id}/approve", response_model=PipelineExecutionResult)
def approve_and_resume(session_id: str, request: ApprovalRequest):
    """Resume a paused pipeline after Human Patent Attorney approval."""
    try:
        result = coordinator.resume_pipeline(
            session_id=session_id,
            human_approved=request.human_approved,
            human_feedback=request.human_feedback,
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


@app.post("/api/v1/eval/benchmark", response_model=EvaluationMetricSummary)
def run_benchmark():
    """Trigger the Golden Dataset evaluation harness for agent regression testing."""
    try:
        evaluator = GoldenDatasetEvaluator()
        return evaluator.run_benchmark()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
