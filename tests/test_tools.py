"""Unit tests for specialized Paper2Patent tools."""

import pytest
from src.tools.paper_extractor import PaperExtractorTool, PaperExtractionInput
from src.tools.prior_art_searcher import PriorArtSearchTool, PriorArtSearchInput
from src.tools.fto_scorer import FTOScorerTool, FTOAnalysisInput
from src.tools.claim_drafter import ClaimDrafterTool, ClaimDraftingInput


def test_paper_extractor_valid(sample_ai_paper):
    tool = PaperExtractorTool()
    inp = PaperExtractionInput(raw_text=sample_ai_paper)
    out = tool.run(inp)

    assert out.is_valid_disclosure is True
    assert "Sub-Quadratic" in out.title
    assert out.domain == "Artificial Intelligence"
    assert len(out.novel_mechanisms) >= 1
    assert "quadratic" in out.abstract_summary.lower()
    assert out.recovery_guide is None


def test_paper_extractor_guided_recovery():
    tool = PaperExtractorTool()
    inp = PaperExtractionInput(raw_text="Short text")
    out = tool.run(inp)

    assert out.is_valid_disclosure is True  # Self-healed
    assert out.recovery_guide is not None
    assert out.recovery_guide.error_code == "INSUFFICIENT_DISCLOSURE_LENGTH"
    assert len(out.recovery_guide.suggested_actions) >= 2


def test_prior_art_searcher(vector_store):
    tool = PriorArtSearchTool(vector_store=vector_store)
    inp = PriorArtSearchInput(query_text="Superconducting Qubit Error Mitigation", domain="Quantum Computing")
    out = tool.run(inp)

    assert out.total_found > 0
    assert len(out.top_hits) > 0
    assert out.top_hits[0].patent_number.startswith("US")


def test_fto_scorer(vector_store):
    search_tool = PriorArtSearchTool(vector_store=vector_store)
    search_out = search_tool.run(PriorArtSearchInput(query_text="State-Space Attention Model"))
    
    fto_tool = FTOScorerTool()
    inp = FTOAnalysisInput(
        paper_title="Selective Recurrence Model",
        novel_mechanisms=["Selective Recurrence Operator"],
        prior_art_hits=search_out.top_hits,
    )
    out = fto_tool.run(inp)

    assert 0.0 <= out.overall_fto_score <= 1.0
    assert len(out.collision_items) > 0
    assert out.risk_category in ["LOW RISK (CLEAN FTO)", "MODERATE RISK (CARVEOUT REQUIRED)", "HIGH RISK (CROWDED ART)"]


def test_claim_drafter():
    tool = ClaimDrafterTool()
    inp = ClaimDraftingInput(
        paper_title="Quantum Cryogenic Controller",
        domain="Quantum Computing",
        novel_mechanisms=["On-chip Josephson waveform generator"],
        fto_carveouts=["Exclude conventional room-temperature microwave generators"],
        num_claims=5,
    )
    out = tool.run(inp)

    assert out.total_claims == 5
    assert out.independent_claim_count >= 2
    assert out.dependent_claim_count >= 1
    assert out.statutory_compliance_score > 0.8
    assert "WHAT IS CLAIMED IS:" in out.formatted_uspto_document
