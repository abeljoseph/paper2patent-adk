"""Base Agent framework compatible with Google ADK (Agent Development Kit)."""

import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.config import settings
from src.observability.tracer import global_tracer


class AgentContext(BaseModel):
    """Context passed across ADK agents during execution."""
    session_id: str
    trace_id: str
    paper_raw: str
    state: Dict[str, Any] = Field(default_factory=dict)
    iteration: int = 1


class AgentResponse(BaseModel):
    """Structured response from an ADK Agent."""
    agent_name: str
    status: str  # SUCCESS, REFINEMENT_REQUIRED, ERROR
    content: str
    data: Dict[str, Any] = Field(default_factory=dict)
    tool_calls_made: List[str] = Field(default_factory=list)


class BaseADKAgent:
    """Base class for Google ADK Agent implementations."""

    def __init__(
        self,
        name: str,
        system_instruction: str,
        tools: Optional[List[Any]] = None,
        model_name: Optional[str] = None,
    ):
        self.name = name
        self.system_instruction = system_instruction
        self.tools = tools or []
        self.model_name = model_name or settings.MODEL_NAME
        self._init_genai_client()

    def _init_genai_client(self):
        """Initialize Google GenAI client if credentials are configured."""
        self.genai_client = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception:
                # If library or auth is not initialized, fallback seamlessly
                self.genai_client = None

    def execute(self, context: AgentContext) -> AgentResponse:
        """Core execution method to be overridden by specialized ADK agents."""
        raise NotImplementedError("Subclasses must implement execute(context).")
