"""Short-term conversational and working memory for Paper2Patent ADK."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class AgentMessage(BaseModel):
    """Message item in conversation session memory."""
    role: str  # user, assistant, system, tool
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentWorkingMemory(BaseModel):
    """Working state for an active patent analysis run."""
    session_id: str
    paper_raw_text: Optional[str] = None
    extracted_features: Dict[str, Any] = Field(default_factory=dict)
    prior_art_hits: List[Dict[str, Any]] = Field(default_factory=list)
    fto_risk_matrix: Dict[str, Any] = Field(default_factory=dict)
    drafted_claims: Dict[str, Any] = Field(default_factory=dict)
    compliance_audit: Dict[str, Any] = Field(default_factory=dict)
    user_adjustments: List[str] = Field(default_factory=list)
    current_iteration: int = 1


class SessionMemory:
    """Manages multi-turn conversation and working memory per session."""

    def __init__(self, max_history_tokens: int = 8000):
        self.max_history_tokens = max_history_tokens
        self._conversations: Dict[str, List[AgentMessage]] = {}
        self._working_memory: Dict[str, AgentWorkingMemory] = {}

    def get_or_create_working_memory(self, session_id: str) -> AgentWorkingMemory:
        """Fetch or initialize the working memory state for a session."""
        if session_id not in self._working_memory:
            self._working_memory[session_id] = AgentWorkingMemory(session_id=session_id)
        return self._working_memory[session_id]

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Append a message to the conversation history."""
        if session_id not in self._conversations:
            self._conversations[session_id] = []
        self._conversations[session_id].append(
            AgentMessage(role=role, content=content, metadata=metadata or {})
        )

    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[AgentMessage]:
        """Get recent conversation history."""
        return self._conversations.get(session_id, [])[-limit:]

    def clear_session(self, session_id: str):
        """Clear memory for a given session."""
        self._conversations.pop(session_id, None)
        self._working_memory.pop(session_id, None)
