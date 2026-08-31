"""Unit tests for Persistent SQLite Memory, Token Compaction, and Async I/O."""

import pytest
import asyncio
from src.memory.session_store import SessionMemory
from src.memory.vector_store import VectorMemoryStore


def test_session_memory_lifecycle(tmp_path):
    db_file = str(tmp_path / "test_session.db")
    mem = SessionMemory(db_path=db_file)
    session_id = "test-session-123"

    # Message recording
    mem.add_message(session_id, "user", "Analyze this transformer paper")
    mem.add_message(session_id, "assistant", "Analyzing paper and prior art")

    history = mem.get_conversation_history(session_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"

    # Working memory state persistence
    working = mem.get_or_create_working_memory(session_id)
    working.extracted_features = {"domain": "Artificial Intelligence"}
    mem.save_working_memory(working)

    # Re-instantiate from SQLite to verify persistence
    mem_reloaded = SessionMemory(db_path=db_file)
    working_reloaded = mem_reloaded.get_or_create_working_memory(session_id)
    assert working_reloaded.extracted_features["domain"] == "Artificial Intelligence"

    # Clear
    mem.clear_session(session_id)
    assert len(mem.get_conversation_history(session_id)) == 0


def test_token_aware_context_compaction(tmp_path):
    db_file = str(tmp_path / "test_compaction.db")
    # Low limit of 50 tokens to trigger compaction
    mem = SessionMemory(db_path=db_file, max_history_tokens=40)
    session_id = "compaction-session"

    # Add multiple long messages
    for i in range(8):
        mem.add_message(session_id, "user", f"Turn {i}: Detailed algorithmic formulation and context disclosures with extensive description.")

    working = mem.get_or_create_working_memory(session_id)
    assert working.condensed_summary is not None
    assert "Consolidated Session Context" in working.condensed_summary


@pytest.mark.asyncio
async def test_async_memory_operations(tmp_path):
    db_file = str(tmp_path / "test_async.db")
    mem = SessionMemory(db_path=db_file)
    store = VectorMemoryStore(db_path=db_file)

    msg = await mem.add_message_async("async-sess", "user", "Async message content")
    assert msg.role == "user"

    doc = await store.add_document_async("ASYNC-DOC-1", "Quantum error correction code")
    assert doc.id == "ASYNC-DOC-1"

    hits = await store.search_async("Quantum error correction", top_k=2)
    assert len(hits) > 0


def test_vector_memory_search(tmp_path):
    db_file = str(tmp_path / "test_vector.db")
    store = VectorMemoryStore(db_path=db_file, embedding_dim=64)

    store.add_document(
        doc_id="CUSTOM-PATENT-001",
        text="Novel optical interconnect architecture for photonic tensor accelerators.",
        metadata={"domain": "Photonics", "patent_number": "US-PHOTONIC-001"},
    )

    results = store.search(query="optical photonic accelerator", top_k=3)
    assert len(results) > 0
    assert any(r["id"] == "CUSTOM-PATENT-001" for r in results)


def test_vector_memory_domain_filter(tmp_path):
    db_file = str(tmp_path / "test_domain.db")
    store = VectorMemoryStore(db_path=db_file)
    results = store.search(query="qubit error mitigation", top_k=5, filter_domain="Quantum Computing")
    
    assert len(results) > 0
    for r in results:
        assert r["metadata"].get("domain") == "Quantum Computing"
