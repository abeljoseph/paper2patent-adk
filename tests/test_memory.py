"""Unit tests for Short-term Session Memory and Long-term Vector Memory."""

import pytest
from src.memory.session_store import SessionMemory
from src.memory.vector_store import VectorMemoryStore


def test_session_memory_lifecycle():
    mem = SessionMemory()
    session_id = "test-session-123"

    # Message recording
    mem.add_message(session_id, "user", "Analyze this transformer paper")
    mem.add_message(session_id, "assistant", "Analyzing paper and prior art")

    history = mem.get_conversation_history(session_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"

    # Working memory state
    working = mem.get_or_create_working_memory(session_id)
    working.extracted_features = {"domain": "Artificial Intelligence"}
    assert working.extracted_features["domain"] == "Artificial Intelligence"

    # Clear
    mem.clear_session(session_id)
    assert len(mem.get_conversation_history(session_id)) == 0


def test_vector_memory_search():
    store = VectorMemoryStore(embedding_dim=32)

    # Insert custom patent
    store.add_document(
        doc_id="CUSTOM-PATENT-001",
        text="Novel optical interconnect architecture for photonic tensor accelerators.",
        metadata={"domain": "Photonics", "patent_number": "US-PHOTONIC-001"},
    )

    results = store.search(query="optical photonic accelerator", top_k=3)
    assert len(results) > 0
    assert any(r["id"] == "CUSTOM-PATENT-001" for r in results)


def test_vector_memory_domain_filter():
    store = VectorMemoryStore()
    results = store.search(query="qubit error mitigation", top_k=5, filter_domain="Quantum Computing")
    
    assert len(results) > 0
    for r in results:
        assert r["metadata"].get("domain") == "Quantum Computing"
