"""Unit tests for PII Scrubbing, Model Routing, and Human-in-the-Loop Orchestration."""

import pytest
from src.observability.pii_scrubber import PIIScrubber
from src.agents.router import ModelRouter
from src.agents.coordinator import Paper2PatentCoordinator


def test_pii_scrubber_text():
    dirty_text = (
        "Contact me at inventor@deepmind.com with key AIzaSyD3xAmPlE12345678901234567890123. "
        "Call +1-555-123-4567 or connect to IP 192.168.1.50 using Bearer eyJhbGciOiJIUzI1NiIsIn."
    )
    clean_text = PIIScrubber.scrub_text(dirty_text)

    assert "[REDACTED_EMAIL]" in clean_text
    assert "inventor@deepmind.com" not in clean_text
    assert "[REDACTED_GOOGLE_API_KEY]" in clean_text
    assert "[REDACTED_PHONE]" in clean_text
    assert "[REDACTED_IP]" in clean_text
    assert "Bearer [REDACTED_TOKEN]" in clean_text


def test_pii_scrubber_dict():
    dirty_dict = {
        "api_key": "secret-12345",
        "nested": {
            "password": "my_password",
            "text": "Send info to scientist@university.edu",
        },
    }
    cleaned = PIIScrubber.scrub_data(dirty_dict)

    assert cleaned["api_key"] == "[REDACTED_CREDENTIAL]"
    assert cleaned["nested"]["password"] == "[REDACTED_CREDENTIAL]"
    assert "[REDACTED_EMAIL]" in cleaned["nested"]["text"]


def test_model_router():
    manifest = ModelRouter.get_routing_manifest()
    assert manifest["PaperAnalyzerAgent"] == "gemini-2.0-flash"
    assert manifest["PriorArtExaminerAgent"] == "gemini-2.0-flash"
    assert manifest["PatentClaimDrafterAgent"] == "gemini-2.5-pro"
    assert manifest["IPComplianceAuditorAgent"] == "gemini-2.5-pro"


def test_hitl_workflow(coordinator, sample_ai_paper):
    session_id = "test-hitl-session"
    
    # 1. Run with HITL enabled
    res_paused = coordinator.run_pipeline(
        paper_text=sample_ai_paper,
        session_id=session_id,
        require_human_approval=True,
    )
    assert res_paused.status == "PAUSED_FOR_HUMAN_APPROVAL"
    assert res_paused.total_claims_drafted == 0
    assert res_paused.fto_score > 0

    # 2. Resume after human approval with feedback
    res_resumed = coordinator.resume_pipeline(
        session_id=session_id,
        human_approved=True,
        human_feedback="Incorporate discrete normalization gates limitation.",
    )
    assert res_resumed.status == "COMPLETED"
    assert res_resumed.total_claims_drafted >= 3
    assert res_resumed.patent_readiness_score > 0.5
