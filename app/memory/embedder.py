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

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

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


class OpenAIEmbedder:
    """Real embedding via an OpenAI-compatible `/embeddings` endpoint (sync)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 10.0,
        transport=None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self._transport = transport

    def embed(self, text: str) -> list[float]:
        if not self.api_key:
            raise ValueError("embedding api_key is required for the openai provider")
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            resp = client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    def similarity(self, a: list[float], b: list[float]) -> float:
        return cosine_similarity(a, b)


class FallbackEmbedder:
    """Wraps a primary embedder and falls back to a secondary on failure."""

    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def embed(self, text: str) -> list[float]:
        try:
            return self.primary.embed(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"embedding provider failed, falling back to hashing: {exc}")
            return self.fallback.embed(text)

    def similarity(self, a: list[float], b: list[float]) -> float:
        return cosine_similarity(a, b)


def create_embedder(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
):
    """Build the configured embedder (default: hashing; openai: fallback-wrapped)."""
    from app.core.config import get_config

    cfg = get_config()
    resolved = provider or cfg.embedding_provider
    if resolved == "openai":
        primary = OpenAIEmbedder(
            api_key=api_key or cfg.embedding_api_key,
            model=model or cfg.embedding_model or "text-embedding-3-small",
            base_url=base_url or cfg.embedding_api_base_url or "https://api.openai.com/v1",
            timeout=timeout if timeout is not None else cfg.embedding_timeout_seconds,
        )
        return FallbackEmbedder(primary, HashingEmbedder())
    return HashingEmbedder()
