"""Strategic Model Router for Multi-Agent Workflows."""

from typing import Dict, Any, Optional
from src.config import settings


class ModelRouter:
    """Intelligently routes agents to specialized Gemini model tiers based on task complexity."""

    # Strategic model tiers based on cognitive workload
    AGENT_TIER_MAPPING = {
        "PaperAnalyzerAgent": "gemini-2.0-flash",       # Fast entity extraction & structured parsing
        "PriorArtExaminerAgent": "gemini-2.0-flash",    # Vector ranking & fast collision math
        "PatentClaimDrafterAgent": "gemini-2.5-pro",    # High-reasoning legal claim synthesis
        "IPComplianceAuditorAgent": "gemini-2.5-pro",   # Deep statutory reasoning (35 U.S.C. 101/102/103/112)
    }

    @classmethod
    def get_model_for_agent(cls, agent_name: str, requested_override: Optional[str] = None) -> str:
        """Resolve the optimal model for an agent persona with fallback resilience."""
        if requested_override:
            return requested_override
        
        # Check strategic mapping
        target_model = cls.AGENT_TIER_MAPPING.get(agent_name, settings.MODEL_NAME)
        return target_model

    @classmethod
    def get_routing_manifest(cls) -> Dict[str, str]:
        """Return the current strategic routing table across all agents."""
        return dict(cls.AGENT_TIER_MAPPING)
