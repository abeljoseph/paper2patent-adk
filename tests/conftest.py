"""Shared pytest fixtures for Paper2Patent ADK tests."""

import pytest
from src.memory.vector_store import VectorMemoryStore
from src.memory.session_store import SessionMemory
from src.agents.coordinator import Paper2PatentCoordinator


@pytest.fixture
def sample_ai_paper():
    return """# Sub-Quadratic State-Space Memory Recurrence for Real-Time Sequence Processing

## Abstract
Modern deep neural networks rely heavily on multi-head scaled dot-product attention, which exhibits quadratic O(N^2) memory and compute bottlenecks with sequence length. In this work, we propose 'Selective Structured Recurrence' (SSR), an adaptive continuous-time state-space operator that dynamically modulates gating matrices based on input context. 

## Novel Technical Mechanism
Our primary contribution is a context-dependent state matrix operator B(t) and C(t) combined with a discrete associative scan algorithm. Unlike static convolution filters, the SSR engine filters irrelevant tokens with linear O(N) memory complexity and 3.2x throughput speedup over baseline Transformers on 128k context windows.
"""


@pytest.fixture
def sample_quantum_paper():
    return """# Real-Time Cryogenic Pulse Modulation for Superconducting Qubit Error Mitigation

## Abstract
Quantum processors suffer from phase decoherence and cross-talk during multi-qubit gate operations. We introduce a Cryogenic Pulse Modulation (CPM) controller operating at 20mK that dynamically corrects flux drift in transmon qubit arrays.

## Novel Technical Mechanism
The invention comprises an on-chip Josephson arbitrary waveform generator coupled to an active feedback loop that suppresses thermal drift and reduces gate infidelity to below 0.05% per Clifford operation.
"""


@pytest.fixture
def vector_store():
    return VectorMemoryStore()


@pytest.fixture
def session_memory():
    return SessionMemory()


@pytest.fixture
def coordinator(vector_store):
    return Paper2PatentCoordinator(vector_store=vector_store)
