"""Tests for M4: Hierarchical Memory (L1 episodic / L2 semantic / L3 procedural)."""

import pytest

from app.memory.embedder import HashingEmbedder, cosine_similarity
from app.memory.episodic_memory import EpisodicMemory
from app.memory.semantic_memory import SemanticMemory
from app.memory.procedural_memory import ProceduralMemory
from app.memory.consolidation import MemoryConsolidation
from app.memory.hierarchical import HierarchicalMemory


# ── Embedder ─────────────────────────────────────────────────────────

def test_cosine_similarity_basics():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_embedder_deterministic_and_semantic():
    e = HashingEmbedder()
    assert e.embed("backdoor trigger") == e.embed("backdoor trigger")

    a = e.embed("backdoor trigger neural cleanse anomaly")
    b = e.embed("backdoor trigger neural cleanse anomaly")
    c = e.embed("completely unrelated weather forecast")
    assert e.similarity(a, b) == pytest.approx(1.0)
    assert e.similarity(a, c) < 0.5


# ── L1 Episodic Memory ──────────────────────────────────────────────

def test_episodic_sliding_window():
    mem = EpisodicMemory(window_size=20)
    mem.start_session("s1")
    for i in range(25):
        mem.add({"type": "observation", "tool": f"tool_{i}"})
    entries = mem.recent()
    assert len(entries) == 20
    assert entries[0]["tool"] == "tool_5"     # oldest 5 evicted
    assert entries[-1]["tool"] == "tool_24"


def test_episodic_keyword_search():
    mem = EpisodicMemory(window_size=20)
    mem.start_session("s1")
    mem.add({"type": "observation", "tool": "strip_detect", "risk_level": "HIGH"})
    mem.add({"type": "observation", "tool": "neural_cleanse"})
    hits = mem.search("strip")
    assert len(hits) >= 1
    assert hits[0]["tool"] == "strip_detect"


def test_episodic_clear():
    mem = EpisodicMemory()
    mem.start_session("s1")
    mem.add({"type": "x"})
    mem.clear()
    assert mem.recent() == []


# ── L2 Semantic Memory ──────────────────────────────────────────────

def test_semantic_search_relevance(tmp_path):
    mem = SemanticMemory(filepath=str(tmp_path / "sem.json"))
    mem.add_finding("model layer.4.conv2 shows abnormal activation",
                    metadata={"tool": "activation_clustering"})
    mem.add_finding("neural cleanse recovered a trigger pattern",
                    metadata={"tool": "neural_cleanse"})
    hits = mem.search("abnormal activation in conv layer")
    assert hits[0]["metadata"]["tool"] == "activation_clustering"


def test_semantic_persistence(tmp_path):
    fp = str(tmp_path / "sem.json")
    mem = SemanticMemory(filepath=fp)
    mem.add_finding("backdoor signature xyz")
    reloaded = SemanticMemory(filepath=fp)
    assert reloaded.snapshot()["findings_count"] == 1


# ── L3 Procedural Memory ────────────────────────────────────────────

def test_procedural_match_strategy(tmp_path):
    mem = ProceduralMemory(filepath=str(tmp_path / "proc.json"))
    mem.add_rule({
        "architecture": "resnet", "task": "detection",
        "strategy": ["strip_detect", "neural_cleanse"],
        "description": "ResNet 系列优先 STRIP + Neural Cleanse",
    })
    matched = mem.match_strategy({"architecture": "resnet", "task": "detection"})
    assert len(matched) == 1
    assert "neural_cleanse" in matched[0]["strategy"]
    assert mem.match_strategy({"architecture": "vgg"}) == []


def test_procedural_search_cases(tmp_path):
    mem = ProceduralMemory(filepath=str(tmp_path / "proc.json"))
    mem.add_case("backdoor via clean-label attack with subtle trigger", metadata={"verified": True})
    hits = mem.search_cases("clean label attack")
    assert len(hits) == 1


# ── Memory Consolidation ────────────────────────────────────────────

def test_consolidation_l1_to_l2(tmp_path):
    ep = EpisodicMemory(window_size=20)
    ep.start_session("s1")
    ep.add({"type": "observation", "tool": "strip_detect", "risk_level": "HIGH",
            "data": {"is_backdoor": True}})
    ep.add({"type": "observation", "tool": "strip_detect", "risk_level": "LOW",
            "data": {"is_backdoor": False}})

    sem = SemanticMemory(filepath=str(tmp_path / "sem.json"))
    proc = ProceduralMemory(filepath=str(tmp_path / "proc.json"))
    promoted = MemoryConsolidation(sem, proc).consolidate_session(ep)
    assert len(promoted) == 1            # only the HIGH-risk entry
    assert sem.snapshot()["findings_count"] == 1


def test_consolidation_l2_to_l3(tmp_path):
    sem = SemanticMemory(filepath=str(tmp_path / "sem.json"))
    sem.add_finding("verified pattern X", metadata={"verified": True})
    sem.add_finding("unverified pattern Y", metadata={})
    proc = ProceduralMemory(filepath=str(tmp_path / "proc.json"))
    promoted = MemoryConsolidation(sem, proc).promote_verified()
    assert len(promoted) == 1
    assert proc.snapshot()["cases_count"] == 1


# ── HierarchicalMemory facade ───────────────────────────────────────

def _make_hierarchical(tmp_path):
    return HierarchicalMemory(
        episodic=EpisodicMemory(window_size=20),
        semantic=SemanticMemory(filepath=str(tmp_path / "sem.json")),
        procedural=ProceduralMemory(filepath=str(tmp_path / "proc.json")),
        use_redis=False,
    )


def test_hierarchical_search_l1_hit(tmp_path):
    hm = _make_hierarchical(tmp_path)
    hm.start_session("s1")
    hm.remember({"type": "observation", "tool": "strip_detect", "content": "entropy result"})
    result = hm.search("strip")
    assert result["layer"] == "episodic"


def test_hierarchical_search_l2_fallback(tmp_path):
    hm = _make_hierarchical(tmp_path)
    hm.start_session("s2")  # empty session -> falls through to L2
    hm.semantic.add_finding("abnormal activation in conv layer")
    result = hm.search("abnormal activation conv")
    assert result["layer"] == "semantic"


def test_hierarchical_consolidate(tmp_path):
    hm = _make_hierarchical(tmp_path)
    hm.start_session("s1")
    hm.remember({"type": "observation", "tool": "strip_detect", "risk_level": "HIGH",
                 "data": {"is_backdoor": True}})
    counts = hm.consolidate()
    assert counts["l1_to_l2"] == 1
    assert hm.semantic.snapshot()["findings_count"] == 1
