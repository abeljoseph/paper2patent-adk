"""Persistent, SQLite-backed Long-Term Semantic Vector Memory with Async Operations."""

import os
import json
import sqlite3
import hashlib
import asyncio
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
    """Persistent SQLite-backed Vector Database supporting semantic search and async task indexing."""

    def __init__(self, db_path: str = "data/paper2patent.db", embedding_dim: int = 256):
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self.documents: Dict[str, DocumentRecord] = {}
        self._ensure_db()
        self._load_from_db()
        if not self.documents:
            self._seed_default_knowledge_base()

    def _ensure_db(self):
        """Initialize SQLite vector store tables."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_records (
                    id TEXT PRIMARY KEY,
                    text TEXT,
                    metadata_json TEXT,
                    embedding_json TEXT
                )
                """
            )
            conn.commit()

    def _load_from_db(self):
        """Load persistent records from SQLite into memory cache."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, text, metadata_json, embedding_json FROM vector_records")
            rows = cur.fetchall()
            for doc_id, text, meta_json, emb_json in rows:
                meta = json.loads(meta_json) if meta_json else {}
                emb = json.loads(emb_json) if emb_json else None
                self.documents[doc_id] = DocumentRecord(
                    id=doc_id,
                    text=text,
                    metadata=meta,
                    embedding=emb,
                )

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate deterministic semantic embedding vector normalized to unit length."""
        words = [w.lower().strip(".,!?:;\"'()[]{}") for w in text.split() if w]
        vec = np.zeros(self.embedding_dim, dtype=np.float32)
        
        if not words:
            vec[0] = 1.0
            return vec.tolist()

        for word in words:
            h_bytes = hashlib.sha256(word.encode("utf-8")).digest()
            idx1 = int.from_bytes(h_bytes[:4], "big") % self.embedding_dim
            idx2 = int.from_bytes(h_bytes[4:8], "big") % self.embedding_dim
            idx3 = int.from_bytes(h_bytes[8:12], "big") % self.embedding_dim

            weight = 1.0 + (len(word) / 6.0)
            vec[idx1] += 2.0 * weight
            vec[idx2] += 1.0 * weight
            vec[idx3] += 0.5 * weight

            if len(word) >= 3:
                for i in range(len(word) - 2):
                    ngram = word[i : i + 3]
                    ng_idx = int.from_bytes(hashlib.md5(ngram.encode("utf-8")).digest()[:4], "big") % self.embedding_dim
                    vec[ng_idx] += 0.3

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentRecord:
        """Add a document to vector memory and persist to SQLite database."""
        embedding = self._generate_embedding(text)
        record = DocumentRecord(
            id=doc_id,
            text=text,
            metadata=metadata or {},
            embedding=embedding,
        )
        self.documents[doc_id] = record

        # Persist to SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO vector_records (id, text, metadata_json, embedding_json)
                VALUES (?, ?, ?, ?)
                """,
                (doc_id, text, json.dumps(metadata or {}), json.dumps(embedding)),
            )
            conn.commit()

        return record

    async def add_document_async(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentRecord:
        """Asynchronous non-blocking document addition."""
        return await asyncio.to_thread(self.add_document, doc_id, text, metadata)

    def search(self, query: str, top_k: int = 5, filter_domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search vector store by cosine similarity with keyword boosting."""
        query_vec = np.array(self._generate_embedding(query), dtype=np.float32)
        query_words = set(w.lower().strip(".,!?:;\"'()[]{}") for w in query.split() if len(w) > 2)
        results = []

        for doc in self.documents.values():
            if filter_domain and doc.metadata.get("domain") != filter_domain:
                continue
            
            doc_vec = np.array(doc.embedding, dtype=np.float32)
            cosine_sim = float(np.dot(query_vec, doc_vec))
            
            doc_words = set(w.lower().strip(".,!?:;\"'()[]{}") for w in doc.text.split() if len(w) > 2)
            common = len(query_words.intersection(doc_words))
            keyword_bonus = min(0.35, common * 0.1)

            sim_score = max(0.0, min(1.0, ((cosine_sim + 1.0) / 2.0) * 0.7 + keyword_bonus))
            
            results.append({
                "id": doc.id,
                "text": doc.text,
                "metadata": doc.metadata,
                "similarity_score": round(sim_score, 4),
            })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

    async def search_async(self, query: str, top_k: int = 5, filter_domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Asynchronous non-blocking vector search."""
        return await asyncio.to_thread(self.search, query, top_k, filter_domain)

    async def background_batch_index(self, docs: List[Dict[str, Any]]):
        """Asynchronous background task to re-index documents."""
        for doc in docs:
            await self.add_document_async(
                doc_id=doc["id"],
                text=doc["text"],
                metadata=doc.get("metadata"),
            )
            await asyncio.sleep(0.01)

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
