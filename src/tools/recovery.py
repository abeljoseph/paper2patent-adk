"""Tool Error Handling and Guided LLM Self-Healing Recovery Specifications."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolRecoveryGuide(BaseModel):
    """Actionable guidance provided to the LLM/Agent when tool execution encounters anomalies."""
    is_recovering: bool = True
    error_code: str
    error_message: str
    suggested_actions: List[str]
    sample_valid_structure: Dict[str, Any] = Field(default_factory=dict)
    remediation_prompt: str
