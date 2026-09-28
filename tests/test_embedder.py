"""Tests for the pluggable embedding provider (default hashing, openai, fallback)."""

import httpx

from app.memory.embedder import (
    HashingEmbedder,
    OpenAIEmbedder,
    FallbackEmbedder,
    create_embedder,
)


def test_create_embedder_default_is_hashing():
    assert isinstance(create_embedder(), HashingEmbedder)


def test_create_embedder_openai_returns_fallback():
    e = create_embedder(
        provider="openai", api_key="sk-test", model="m", base_url="http://x", timeout=1
    )
    assert isinstance(e, FallbackEmbedder)
    assert isinstance(e.primary, OpenAIEmbedder)


def test_openai_embedder_returns_vector():
    def handler(request):
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})

    transport = httpx.MockTransport(handler)
    e = OpenAIEmbedder(api_key="sk", model="m", base_url="http://x", transport=transport)
    assert e.embed("hello") == [0.1, 0.2, 0.3]


def test_fallback_embedder_uses_fallback_on_failure():
    class Boom:
        def embed(self, text):
            raise RuntimeError("boom")

        def similarity(self, a, b):
            return 0.0

    fb = FallbackEmbedder(Boom(), HashingEmbedder(dim=16))
    v = fb.embed("hello")
    assert isinstance(v, list)
    assert len(v) == 16


def test_semantic_memory_default_is_hashing(tmp_path):
    from app.memory.semantic_memory import SemanticMemory

    mem = SemanticMemory(filepath=str(tmp_path / "sem.json"))
    assert isinstance(mem.embedder, HashingEmbedder)
