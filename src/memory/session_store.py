"""Persistent, Token-Aware Short-term and Working Memory backed by SQLite and Async I/O."""

import json
import os
import sqlite3
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class AgentMessage(BaseModel):
    """Message item in conversation session memory."""
    role: str  # user, assistant, system, tool
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
    token_count: int = 0

    def calculate_tokens(self) -> int:
        """Estimate token volume (approx 4 chars per token)."""
        self.token_count = max(1, len(self.content) // 4)
        return self.token_count


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
    condensed_summary: Optional[str] = None
    current_iteration: int = 1


class SessionMemory:
    """Persistent SQLite-backed Session & Working Memory with Token-Aware Context Compaction."""

    def __init__(self, db_path: str = "data/paper2patent.db", max_history_tokens: int = 2000):
        self.db_path = db_path
        self.max_history_tokens = max_history_tokens
        self._ensure_db()
        self._cache_working: Dict[str, AgentWorkingMemory] = {}

    def _ensure_db(self):
        """Initialize SQLite persistent storage tables."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    paper_raw_text TEXT,
                    state_json TEXT,
                    condensed_summary TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    metadata_json TEXT,
                    token_count INTEGER,
                    timestamp TEXT
                )
                """
            )
            conn.commit()

    def get_or_create_working_memory(self, session_id: str) -> AgentWorkingMemory:
        """Fetch working memory from SQLite database with local caching."""
        if session_id in self._cache_working:
            return self._cache_working[session_id]

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT paper_raw_text, state_json, condensed_summary FROM sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if row:
                paper_raw, state_raw, summary = row
                state = json.loads(state_raw) if state_raw else {}
                wm = AgentWorkingMemory(
                    session_id=session_id,
                    paper_raw_text=paper_raw,
                    extracted_features=state.get("extracted_features", {}),
                    prior_art_hits=state.get("prior_art_hits", []),
                    fto_risk_matrix=state.get("fto_risk_matrix", {}),
                    drafted_claims=state.get("drafted_claims", {}),
                    compliance_audit=state.get("compliance_audit", {}),
                    user_adjustments=state.get("user_adjustments", []),
                    condensed_summary=summary,
                    current_iteration=state.get("current_iteration", 1),
                )
            else:
                wm = AgentWorkingMemory(session_id=session_id)
                conn.execute(
                    "INSERT INTO sessions (session_id, paper_raw_text, state_json, condensed_summary, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, "", "{}", "", datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()

        self._cache_working[session_id] = wm
        return wm

    def save_working_memory(self, working_memory: AgentWorkingMemory):
        """Persist active working memory to SQLite database."""
        self._cache_working[working_memory.session_id] = working_memory
        state = {
            "extracted_features": working_memory.extracted_features,
            "prior_art_hits": working_memory.prior_art_hits,
            "fto_risk_matrix": working_memory.fto_risk_matrix,
            "drafted_claims": working_memory.drafted_claims,
            "compliance_audit": working_memory.compliance_audit,
            "user_adjustments": working_memory.user_adjustments,
            "current_iteration": working_memory.current_iteration,
        }
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sessions SET 
                    paper_raw_text = ?, 
                    state_json = ?, 
                    condensed_summary = ?, 
                    updated_at = ?
                WHERE session_id = ?
                """,
                (
                    working_memory.paper_raw_text or "",
                    json.dumps(state),
                    working_memory.condensed_summary or "",
                    datetime.now(timezone.utc).isoformat(),
                    working_memory.session_id,
                ),
            )
            conn.commit()

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> AgentMessage:
        """Add message, persist to SQLite, and execute token-aware compaction if limit is exceeded."""
        msg = AgentMessage(role=role, content=content, metadata=metadata or {})
        msg.calculate_tokens()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata_json, token_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, json.dumps(metadata or {}), msg.token_count, msg.timestamp),
            )
            conn.commit()

        # Run token-aware compaction
        self._compact_history_if_needed(session_id)
        return msg

    async def add_message_async(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> AgentMessage:
        """Asynchronous non-blocking message addition."""
        return await asyncio.to_thread(self.add_message, session_id, role, content, metadata)

    def _compact_history_if_needed(self, session_id: str):
        """Token-aware compaction: Summarizes older messages into a consolidated context summary."""
        messages = self.get_conversation_history(session_id, limit=100)
        total_tokens = sum(m.token_count for m in messages)

        if total_tokens > self.max_history_tokens and len(messages) > 4:
            # Keep newest 3 messages, compact earlier into summary
            to_compact = messages[:-3]
            summary_points = [f"[{m.role.upper()}]: {m.content[:120]}..." for m in to_compact]
            condensed = "Consolidated Session Context:\n" + "\n".join(summary_points)
            
            wm = self.get_or_create_working_memory(session_id)
            wm.condensed_summary = (wm.condensed_summary or "") + "\n" + condensed
            self.save_working_memory(wm)

            # Prune compacted messages from SQLite
            compact_ids = [m.metadata.get("id") for m in to_compact if m.metadata.get("id")]
            if compact_ids:
                with sqlite3.connect(self.db_path) as conn:
                    conn.executemany("DELETE FROM messages WHERE id = ?", [(i,) for i in compact_ids])
                    conn.commit()

    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[AgentMessage]:
        """Fetch conversation messages from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, role, content, metadata_json, token_count, timestamp FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            )
            rows = cur.fetchall()

        messages = []
        for row in reversed(rows):
            mid, role, content, meta_json, tok, ts = row
            meta = json.loads(meta_json) if meta_json else {}
            meta["id"] = mid
            msg = AgentMessage(role=role, content=content, metadata=meta, timestamp=ts, token_count=tok or len(content)//4)
            messages.append(msg)
        return messages

    async def get_conversation_history_async(self, session_id: str, limit: int = 10) -> List[AgentMessage]:
        """Asynchronous fetch for conversation history."""
        return await asyncio.to_thread(self.get_conversation_history, session_id, limit)

    def clear_session(self, session_id: str):
        """Purge session data from SQLite database."""
        self._cache_working.pop(session_id, None)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
