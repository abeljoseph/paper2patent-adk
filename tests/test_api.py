"""FastAPI endpoint tests for Paper2Patent service."""

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


def test_analyze_endpoint_invalid_short():
    response = client.post(
        "/api/v1/analyze",
        json={"paper_text": "Short"},
    )
    # Validation error because min_length=20
    assert response.status_code == 422
