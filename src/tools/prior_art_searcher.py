"""Tool for searching patent prior art and semantic citations across patent databases."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.memory.vector_store import VectorMemoryStore
from src.observability.tracer import trace_agent_step


class PriorArtSearchInput(BaseModel):
    """Input parameters for prior art patent search."""
    query_text: str = Field(..., description="Query summary or technical disclosure mechanism to match.")
    domain: Optional[str] = Field(None, description="Optional domain filter (e.g., 'Quantum Computing', 'Artificial Intelligence').")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of prior art candidates to retrieve.")


class PatentHit(BaseModel):
    """Patent search hit result."""
    patent_id: str
    patent_number: str
    title: str
    assignee: str
    filing_year: int
    similarity_score: float
    abstract_snippet: str
    potential_overlap: str


class PriorArtSearchOutput(BaseModel):
    """Result of semantic prior art search."""
    total_found: int
    top_hits: List[PatentHit]
    search_summary: str


class PriorArtSearchTool:
    """Tool that scans the patent knowledge base for semantic prior art."""

    name: str = "prior_art_searcher"
    description: str = "Searches patent repositories (USPTO/WIPO) for semantically related prior art disclosures."

    def __init__(self, vector_store: Optional[VectorMemoryStore] = None):
        self.vector_store = vector_store or VectorMemoryStore()

    @trace_agent_step(agent_name="PriorArtSearchTool", step_name="search_prior_art", component_type="tool")
    def run(self, input_data: PriorArtSearchInput, trace_id: Optional[str] = None) -> PriorArtSearchOutput:
        """Execute prior art search against vector database."""
        raw_results = self.vector_store.search(
            query=input_data.query_text,
            top_k=input_data.top_k,
            filter_domain=input_data.domain,
        )

        hits: List[PatentHit] = []
        for r in raw_results:
            meta = r.get("metadata", {})
            if meta.get("type") == "statute":
                continue  # Skip legal statutes from prior art hits
            
            sim = r.get("similarity_score", 0.5)
            overlap_desc = (
                "High conceptual overlap in primary operational equations."
                if sim > 0.8
                else "Moderate contextual similarity in background architecture."
                if sim > 0.6
                else "Low overlap; peripheral prior art."
            )

            hits.append(
                PatentHit(
                    patent_id=r.get("id", "UNKNOWN"),
                    patent_number=meta.get("patent_number", r.get("id", "US-PATENT")),
                    title=meta.get("title", "Prior Art Document"),
                    assignee=meta.get("assignee", "Unknown Assignee"),
                    filing_year=meta.get("filing_year", 2020),
                    similarity_score=sim,
                    abstract_snippet=r.get("text", "")[:180] + "...",
                    potential_overlap=overlap_desc,
                )
            )

        summary = (
            f"Retrieved {len(hits)} prior art patent reference(s) for query under domain '{input_data.domain or 'All Domains'}'."
        )

        return PriorArtSearchOutput(
            total_found=len(hits),
            top_hits=hits,
            search_summary=summary,
        )
