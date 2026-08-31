"""Tool for Freedom-to-Operate (FTO) risk scoring and prior art collision analysis."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.tools.prior_art_searcher import PatentHit
from src.observability.tracer import trace_agent_step


class FTOAnalysisInput(BaseModel):
    """Input payload for FTO collision scoring."""
    paper_title: str
    novel_mechanisms: List[str]
    prior_art_hits: List[PatentHit]


class CollisionItem(BaseModel):
    """Specific collision analysis against an identified prior patent."""
    patent_number: str
    patent_title: str
    collision_probability: float
    risk_level: str  # LOW, MODERATE, HIGH
    conflicting_element: str
    carveout_strategy: str


class FTOAnalysisOutput(BaseModel):
    """Comprehensive Freedom-to-Operate analysis report."""
    overall_fto_score: float  # 0.0 (High Risk) to 1.0 (Completely Clean)
    risk_category: str  # LOW RISK (CLEAN), MODERATE RISK (CARVEOUT NEEDED), HIGH RISK (POTENTIAL INFRINGEMENT)
    collision_items: List[CollisionItem]
    patentability_assessment: str
    recommended_claim_scope: str


class FTOScorerTool:
    """Tool that calculates patent collision indices and Freedom-to-Operate clearance."""

    name: str = "fto_scorer"
    description: str = "Calculates Freedom-to-Operate (FTO) collision probabilities and carves out patentable claim boundaries."

    @trace_agent_step(agent_name="FTOScorerTool", step_name="calculate_fto_collision", component_type="tool")
    def run(self, input_data: FTOAnalysisInput, trace_id: Optional[str] = None) -> FTOAnalysisOutput:
        """Evaluate collision risk against candidate prior art patents."""
        collision_items: List[CollisionItem] = []
        max_collision_prob = 0.0

        for hit in input_data.prior_art_hits:
            # Mathematical probability derived from similarity score
            sim = hit.similarity_score
            collision_prob = round(min(0.95, max(0.05, sim * 0.92)), 3)
            max_collision_prob = max(max_collision_prob, collision_prob)

            if collision_prob >= 0.75:
                risk_lvl = "HIGH"
                conflicting = f"Primary architectural pipeline overlaps with {hit.patent_number} core claims."
                carveout = f"Narrow independent claims to specify explicit non-standard topological routing distinct from {hit.assignee}'s patent."
            elif collision_prob >= 0.55:
                risk_lvl = "MODERATE"
                conflicting = f"Sub-component recurrence matrix shares functional similarities with {hit.patent_number}."
                carveout = "Introduce dependent claim limitations covering the specific training parameterization."
            else:
                risk_lvl = "LOW"
                conflicting = "No direct operational overlap detected."
                carveout = "Maintain broad claim terminology."

            collision_items.append(
                CollisionItem(
                    patent_number=hit.patent_number,
                    patent_title=hit.title,
                    collision_probability=collision_prob,
                    risk_level=risk_lvl,
                    conflicting_element=conflicting,
                    carveout_strategy=carveout,
                )
            )

        # Invert collision to obtain Freedom-to-Operate score (Higher = Cleaner)
        fto_score = round(max(0.1, 1.0 - (max_collision_prob * 0.75)), 2)

        if fto_score >= 0.70:
            category = "LOW RISK (CLEAN FTO)"
            assessment = "Strong novel technical subject matter with clear daylight from existing prior art."
            scope = "Broad independent claims feasible with strong defensive perimeter."
        elif fto_score >= 0.45:
            category = "MODERATE RISK (CARVEOUT REQUIRED)"
            assessment = "Patentable subject matter exists, but claims must explicitly exclude prior art mechanisms."
            scope = "Intermediate claim scope focusing on specialized hardware integration or specific loss constraints."
        else:
            category = "HIGH RISK (CROWDED ART)"
            assessment = "Highly crowded patent landscape; significant risk of 35 U.S.C. 102/103 rejection without surgical claim drafting."
            scope = "Narrow embodiment claims focused strictly on proprietary deployment topologies."

        return FTOAnalysisOutput(
            overall_fto_score=fto_score,
            risk_category=category,
            collision_items=collision_items,
            patentability_assessment=assessment,
            recommended_claim_scope=scope,
        )
