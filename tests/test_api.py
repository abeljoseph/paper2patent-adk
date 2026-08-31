"""FastAPI endpoint tests for Paper2Patent service with HITL and Benchmarks."""

import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "adk_framework" in data
    assert "SQLite" in data["storage"]


def test_analyze_endpoint_valid(sample_ai_paper):
    response = client.post(
        "/api/v1/analyze",
        json={"paper_text": sample_ai_paper, "max_refinement_cycles": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "Artificial Intelligence"
    assert "drafted_claims" in data
    assert data["total_claims_drafted"] >= 3

    # Check trace retrieval
    trace_id = data["trace_id"]
    trace_resp = client.get(f"/api/v1/traces/{trace_id}")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert trace_data["trace_id"] == trace_id
    assert len(trace_data["spans"]) >= 4


def test_hitl_approval_endpoint(sample_ai_paper):
    # 1. Start pipeline with HITL enabled
    start_resp = client.post(
        "/api/v1/analyze",
        json={"paper_text": sample_ai_paper, "require_human_approval": True, "session_id": "api-hitl-sess"},
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "PAUSED_FOR_HUMAN_APPROVAL"

    # 2. Approve and resume
    approve_resp = client.post(
        "/api/v1/pipeline/api-hitl-sess/approve",
        json={"human_approved": True, "human_feedback": "Ensure discrete gates limitation in claim 2."},
    )
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()
    assert approve_data["status"] == "COMPLETED"
    assert approve_data["total_claims_drafted"] >= 3


def test_benchmark_endpoint():
    response = client.post("/api/v1/eval/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert data["total_test_cases"] >= 3
    assert data["overall_pass_rate"] >= 0.90


def test_analyze_endpoint_invalid_short():
    response = client.post(
        "/api/v1/analyze",
        json={"paper_text": "Short"},
    )
    assert response.status_code == 422
