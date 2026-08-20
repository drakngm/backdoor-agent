"""
Embedder: text -> vector, plus cosine similarity.

MVP uses a deterministic bag-of-words hashing embedder (pure Python, zero deps).
The interface is intentionally minimal so it can be swapped for a real embedding
service (e.g. OpenAI `text-embedding-3-small`) in production:

    class OpenAIEmbedder:
        def embed(self, text): return client.embeddings.create(...)
        def similarity(self, a, b): return cosine_similarity(a, b)
"""

import hashlib
import math
import re
from typing import Protocol

# ASCII words + individual CJK characters (Chinese has no spaces).
_TOKEN_RE = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]")


class EmbedderLike(Protocol):
    """Minimal embedder interface (pluggable: hashing, numpy, OpenAI, ...)."""

    def embed(self, text: str) -> list[float]: ...

    def similarity(self, a: list[float], b: list[float]) -> float: ...


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors (pure Python)."""
    if len(a) != len(b):
        raise ValueError("vectors must have equal length")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class HashingEmbedder:
    """
    Deterministic hashing-trick embedder.

    Each token is hashed into a fixed-size bucket (no vocabulary needed), the
    count vector is L2-normalized. Stable across runs (uses MD5, not Python's
    randomized `hash`), so persisted vectors remain comparable.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN_RE.findall(text.lower()):
            bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[bucket] += 1.0

        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def similarity(self, a: list[float], b: list[float]) -> float:
        return cosine_similarity(a, b)
