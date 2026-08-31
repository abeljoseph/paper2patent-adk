"""Integration tests for Google ADK Multi-Agent Orchestration."""

import pytest
from src.agents.coordinator import Paper2PatentCoordinator


def test_coordinator_end_to_end_ai(coordinator, sample_ai_paper):
    result = coordinator.run_pipeline(paper_text=sample_ai_paper)

    assert result.paper_title != ""
    assert result.domain == "Artificial Intelligence"
    assert 0.0 <= result.fto_score <= 1.0
    assert result.patent_readiness_score > 0.5
    assert result.verdict in ["READY_FOR_PROVISIONAL_FILING", "REFINEMENT_RECOMMENDED"]
    assert result.total_claims_drafted >= 3
    assert len(result.drafted_claims.get("claims", [])) == 5
    assert "PATENT COOPERATION TREATY / USPTO" in result.formatted_dossier
    assert result.metrics.steps_count >= 4
    assert result.metrics.total_tokens > 0


def test_coordinator_end_to_end_quantum(coordinator, sample_quantum_paper):
    result = coordinator.run_pipeline(paper_text=sample_quantum_paper)

    assert result.domain == "Quantum Computing"
    assert "Josephson" in str(result.extracted_disclosure)
    assert result.total_claims_drafted == 5
    assert result.metrics.total_duration_ms >= 0


def test_coordinator_invalid_text(coordinator):
    with pytest.raises(ValueError, match="Paper analysis failed"):
        coordinator.run_pipeline(paper_text="too short")
