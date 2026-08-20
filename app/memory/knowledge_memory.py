"""
L4: Knowledge Memory — RAG knowledge base (placeholder).

Lifecycle: persistent
Capacity: large-scale knowledge base
Storage: in-memory list[dict] (MVP) → vector DB in production

Holds curated knowledge about backdoor attacks:
  - Known threat signatures
  - Mitigation best practices
  - Reference papers

Current MVP: returns hardcoded knowledge entries.
Future: embedding-based semantic search.
"""

from typing import Any, Optional

from app.memory.base import BaseMemory


class KnowledgeMemory(BaseMemory):
    """
    Knowledge base for RAG-style retrieval.

    MVP implementation: stores documents as dicts in memory,
    search() returns keyword-matched results.

    Production path:
      - Replace with ChromaDB / Pinecone / pgvector
      - Add embedding generation pipeline
      - Enable hybrid search (keyword + semantic)
    """

    def __init__(self):
        self._storage: dict[str, Any] = {}

        # Pre-loaded security knowledge
        self.documents: list[dict[str, Any]] = [
            {
                "id": "kb-001",
                "title": "STRIP Detection Method",
                "content": (
                    "STRIP (STRong Intentional Perturbation) detects backdoors "
                    "by systematically perturbing input samples and measuring "
                    "output entropy. High entropy variance indicates a potential "
                    "backdoor trigger. Effective for fast CI/CD scans."
                ),
                "tags": ["strip", "detection", "fast_scan"],
                "source": "STRIP: A Defence Against Trojan Attacks on Deep Neural Networks (Gao et al., 2019)",
            },
            {
                "id": "kb-002",
                "title": "Neural Cleanse Methodology",
                "content": (
                    "Neural Cleanse reverse-engineers potential backdoor triggers "
                    "via gradient-based optimization. It applies MAD (Median Absolute "
                    "Deviation) outlier detection on recovered trigger L1 norms to "
                    "identify anomalous (backdoored) classes. Best for deep scans."
                ),
                "tags": ["neural_cleanse", "detection", "deep_scan"],
                "source": "Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks (Wang et al., 2019)",
            },
            {
                "id": "kb-003",
                "title": "Activation Clustering Technique",
                "content": (
                    "Activation Clustering extracts intermediate layer activations "
                    "from clean and potentially backdoored samples, then applies "
                    "PCA/t-SNE + K-Means to detect anomalous clusters. Anomalous "
                    "separation suggests backdoor presence."
                ),
                "tags": ["activation_clustering", "detection", "deep_scan"],
                "source": "Activation Clustering for Backdoor Detection (Şerban & Xu, 2020)",
            },
            {
                "id": "kb-004",
                "title": "Spectral Signature Analysis",
                "content": (
                    "Spectral Signature Analysis decomposes the model's weight "
                    "matrices using SVD to detect anomalous spectral patterns "
                    "introduced by backdoor poisoning."
                ),
                "tags": ["spectral_signature", "detection", "forensic_scan"],
                "source": "Spectral Signatures in Backdoor Attacks (Tran et al., 2018)",
            },
            {
                "id": "kb-005",
                "title": "Backdoor Defense Best Practices",
                "content": (
                    "1. Regularly scan models before deployment. "
                    "2. Use multiple detection methods (ensemble). "
                    "3. Monitor model behavior in production. "
                    "4. Maintain a model registry with versioning. "
                    "5. Apply input sanitization and output monitoring."
                ),
                "tags": ["best_practices", "defense"],
                "source": "AI Security Guidelines",
            },
        ]

    # ── BaseMemory interface ────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def retrieve(self, key: str) -> Optional[Any]:
        return self._storage.get(key)

    def clear(self) -> None:
        self._storage.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "documents_count": len(self.documents),
            "storage": dict(self._storage),
        }

    # ── RAG Query ───────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search knowledge base for relevant documents.

        MVP: simple keyword matching (case-insensitive).
        Production: embedding-based semantic search.

        Args:
            query: Search query string.
            top_k: Max results to return.

        Returns:
            List of matching documents with relevance scores.
        """
        query_lower = query.lower()
        scored: list[tuple[dict[str, Any], int]] = []

        for doc in self.documents:
            # Score by keyword occurrence
            score = 0
            searchable = f"{doc.get('title', '')} {doc.get('content', '')} {' '.join(doc.get('tags', []))}".lower()

            for word in query_lower.split():
                if word in searchable:
                    score += searchable.count(word)

            if score > 0:
                scored.append((doc, score))

        # Sort by relevance descending, take top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for doc, score in scored[:top_k]:
            results.append({**doc, "relevance_score": score})

        return results

    def ingest(self, document: dict[str, Any]) -> None:
        """
        Add a new document to the knowledge base.

        Args:
            document: Dict with 'title', 'content', 'tags', 'source'.
        """
        doc_id = f"kb-{len(self.documents) + 1:03d}"
        document["id"] = doc_id
        self.documents.append(document)

    def get_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Retrieve all documents matching a tag."""
        return [d for d in self.documents if tag in d.get("tags", [])]

    def get_by_id(self, doc_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a document by its ID."""
        for doc in self.documents:
            if doc.get("id") == doc_id:
                return doc
        return None