"""Base Agent framework compatible with Google ADK (Agent Development Kit) with Async & Model Routing."""

import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.config import settings
from src.agents.router import ModelRouter


class AgentContext(BaseModel):
    """Context passed across ADK agents during execution."""
    session_id: str
    trace_id: str
    paper_raw: str
    state: Dict[str, Any] = Field(default_factory=dict)
    iteration: int = 1
    requires_human_approval: bool = False
    human_approved: bool = False
    human_feedback: Optional[str] = None


class AgentResponse(BaseModel):
    """Structured response from an ADK Agent."""
    agent_name: str
    model_used: str = "gemini-2.0-flash"
    status: str  # SUCCESS, REFINEMENT_REQUIRED, PAUSED_FOR_HUMAN_APPROVAL, ERROR
    content: str
    data: Dict[str, Any] = Field(default_factory=dict)
    tool_calls_made: List[str] = Field(default_factory=list)


class BaseADKAgent:
    """Base class for Google ADK Agent implementations with strategic model routing."""

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
        # Strategic model routing
        self.model_name = ModelRouter.get_model_for_agent(name, model_name)
        self._init_genai_client()

    def _init_genai_client(self):
        """Initialize Google GenAI client if credentials are configured."""
        self.genai_client = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception:
                self.genai_client = None

    def execute(self, context: AgentContext) -> AgentResponse:
        """Core synchronous execution method to be overridden by specialized ADK agents."""
        raise NotImplementedError("Subclasses must implement execute(context).")

    async def execute_async(self, context: AgentContext) -> AgentResponse:
        """Asynchronous execution handler."""
        return await asyncio.to_thread(self.execute, context)
