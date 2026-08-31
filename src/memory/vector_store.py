"""Long-term semantic vector memory for Prior Art, Lab IP, and Patent Statues."""

import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    """Semantic vector record."""
    id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class VectorMemoryStore:
    """In-memory Vector Database supporting semantic search over Patent prior art."""

    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.documents: Dict[str, DocumentRecord] = {}
        self._seed_default_knowledge_base()

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate deterministic semantic embedding vector normalized to unit length."""
        words = [w.lower().strip(".,!?:;\"'()[]{}") for w in text.split() if w]
        vec = np.zeros(self.embedding_dim, dtype=np.float32)
        
        if not words:
            vec[0] = 1.0
            return vec.tolist()

        for word in words:
            # Deterministic SHA256 hashing
            h_bytes = hashlib.sha256(word.encode("utf-8")).digest()
            idx1 = int.from_bytes(h_bytes[:4], "big") % self.embedding_dim
            idx2 = int.from_bytes(h_bytes[4:8], "big") % self.embedding_dim
            idx3 = int.from_bytes(h_bytes[8:12], "big") % self.embedding_dim

            weight = 1.0 + (len(word) / 6.0)
            vec[idx1] += 2.0 * weight
            vec[idx2] += 1.0 * weight
            vec[idx3] += 0.5 * weight

            # Character 3-grams for fuzzy sub-word matching
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    ngram = word[i : i + 3]
                    ng_idx = int.from_bytes(hashlib.md5(ngram.encode("utf-8")).digest()[:4], "big") % self.embedding_dim
                    vec[ng_idx] += 0.3

        # Normalize to unit vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentRecord:
        """Add a document to vector memory with embedding."""
        embedding = self._generate_embedding(text)
        record = DocumentRecord(
            id=doc_id,
            text=text,
            metadata=metadata or {},
            embedding=embedding,
        )
        self.documents[doc_id] = record
        return record

    def search(self, query: str, top_k: int = 5, filter_domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search vector store by cosine similarity."""
        query_vec = np.array(self._generate_embedding(query), dtype=np.float32)
        query_words = set(w.lower().strip(".,!?:;\"'()[]{}") for w in query.split() if len(w) > 2)
        results = []

        for doc in self.documents.values():
            if filter_domain and doc.metadata.get("domain") != filter_domain:
                continue
            
            doc_vec = np.array(doc.embedding, dtype=np.float32)
            cosine_sim = float(np.dot(query_vec, doc_vec))
            
            # Keyword overlap bonus
            doc_words = set(w.lower().strip(".,!?:;\"'()[]{}") for w in doc.text.split() if len(w) > 2)
            common = len(query_words.intersection(doc_words))
            keyword_bonus = min(0.35, common * 0.1)

            # Combined similarity score
            sim_score = max(0.0, min(1.0, ((cosine_sim + 1.0) / 2.0) * 0.7 + keyword_bonus))
            
            results.append({
                "id": doc.id,
                "text": doc.text,
                "metadata": doc.metadata,
                "similarity_score": round(sim_score, 4),
            })

        # Sort descending by similarity
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

    def _seed_default_knowledge_base(self):
        """Seed representative patent prior art and statutory examination rules."""
        seed_patents = [
            {
                "id": "US10452981B2",
                "text": "Self-attention mechanism and multi-head neural network architectures for sequence transduction and natural language processing tasks using scaled dot-product attention.",
                "metadata": {
                    "patent_number": "US-10452981-B2",
                    "title": "Attention-based sequence transduction neural networks",
                    "domain": "Artificial Intelligence",
                    "assignee": "Google LLC",
                    "filing_year": 2017,
                },
            },
            {
                "id": "US11874291B1",
                "text": "State-space models and structured matrix recurrence operators for sub-quadratic context window sequence modeling and efficient inference.",
                "metadata": {
                    "patent_number": "US-11874291-B1",
                    "title": "Selective State-Space Architecture for Scalable Sequence Processing",
                    "domain": "Artificial Intelligence",
                    "assignee": "DeepTech Labs",
                    "filing_year": 2023,
                },
            },
            {
                "id": "US9845341B2",
                "text": "Superconducting flux qubit control circuits using cryogenic microwave pulses and error mitigation topologies for fault-tolerant quantum computing.",
                "metadata": {
                    "patent_number": "US-9845341-B2",
                    "title": "Superconducting Qubit Calibration and Error Mitigation",
                    "domain": "Quantum Computing",
                    "assignee": "IBM Corp",
                    "filing_year": 2019,
                },
            },
            {
                "id": "US10923849B2",
                "text": "Topological quantum gate synthesizers and Majorana zero mode braiding protocols in semiconductor-superconductor heterostructures.",
                "metadata": {
                    "patent_number": "US-10923849-B2",
                    "title": "Topological Quantum Gate Control and Stabilizer Codes",
                    "domain": "Quantum Computing",
                    "assignee": "Microsoft Corp",
                    "filing_year": 2021,
                },
            },
            {
                "id": "US11234988B2",
                "text": "Engineered Cas12a ribonucleoprotein complexes with modified PAM recognition motifs for targeted genomic transcriptional activation.",
                "metadata": {
                    "patent_number": "US-11234988-B2",
                    "title": "Targeted Genomic Editing with Modified Cas Effector Nucleases",
                    "domain": "Biotechnology",
                    "assignee": "Broad Institute",
                    "filing_year": 2020,
                },
            },
            # Statutory Patent Examination Rules
            {
                "id": "35-USC-101",
                "text": "Patentable subject matter requires a new and useful process, machine, manufacture, or composition of matter, excluding abstract mathematical algorithms unless tied to a technical application.",
                "metadata": {"type": "statute", "section": "35 U.S.C. 101"},
            },
            {
                "id": "35-USC-102",
                "text": "Novelty condition: an invention cannot be patented if disclosed in prior art publications or patents anywhere in the world prior to the effective filing date.",
                "metadata": {"type": "statute", "section": "35 U.S.C. 102"},
            },
            {
                "id": "35-USC-103",
                "text": "Non-obviousness: claimed subject matter must not have been obvious at the time of invention to a person having ordinary skill in the art (PHOSITA).",
                "metadata": {"type": "statute", "section": "35 U.S.C. 103"},
            },
            {
                "id": "35-USC-112",
                "text": "Written description and enablement requirement: the specification must describe the invention in clear, concise terms enabling any person skilled in the art to make and use it.",
                "metadata": {"type": "statute", "section": "35 U.S.C. 112"},
            },
        ]

        for p in seed_patents:
            self.add_document(doc_id=p["id"], text=p["text"], metadata=p["metadata"])
