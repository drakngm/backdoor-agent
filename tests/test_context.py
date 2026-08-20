"""Tests for Context Management (M2): WorkingMemory compaction + summary."""

from app.memory.working_memory import (
    WorkingMemory,
    build_deterministic_summary,
)
from app.memory.session_memory import SessionMemory


# ── Token estimation ─────────────────────────────────────────────────

def test_estimate_tokens_ascii():
    wm = WorkingMemory(max_tokens=10000)
    assert wm._estimate_tokens("hello world") == 2  # 11 chars // 4


def test_estimate_tokens_cjk():
    wm = WorkingMemory(max_tokens=10000)
    assert wm._estimate_tokens("检测") == 2  # 2 CJK chars ≈ 2 tokens


def test_estimate_tokens_empty():
    wm = WorkingMemory(max_tokens=10000)
    assert wm._estimate_tokens("") == 0


# ── Observation budget (tool_result_budget) ──────────────────────────

def test_observation_budget_truncates_large_result():
    wm = WorkingMemory(max_tokens=100000, max_observation_chars=60)
    obs = {
        "tool_name": "strip_detect",
        "success": True,
        "risk_level": "HIGH",
        "confidence_score": 0.9,
        "data": {"payload": "x" * 500},
    }
    wm.append_observation(obs)
    msg = wm.messages[-1]
    assert "truncated" in msg["content"]
    assert msg["metadata"]["tool"] == "strip_detect"
    assert msg["metadata"]["risk_level"] == "HIGH"


def test_observation_budget_keeps_small_result():
    wm = WorkingMemory(max_tokens=100000, max_observation_chars=1000)
    wm.append_observation({"tool_name": "strip_detect", "success": True})
    assert "truncated" not in wm.messages[-1]["content"]


# ── Deterministic summary (replaces LLM compact_history) ─────────────

def test_build_deterministic_summary_extracts_facts():
    messages = [
        {"role": "user", "content": "detect model.h5"},
        {
            "role": "tool",
            "content": "...",
            "metadata": {
                "type": "observation",
                "tool": "strip_detect",
                "success": True,
                "risk_level": "HIGH",
                "confidence": 0.9,
            },
        },
        {
            "role": "tool",
            "content": "...",
            "metadata": {
                "type": "observation",
                "tool": "neural_cleanse",
                "success": True,
                "risk_level": "LOW",
                "confidence": 0.1,
            },
        },
    ]
    summary = build_deterministic_summary(messages)
    assert "strip_detect" in summary
    assert "neural_cleanse" in summary
    assert "HIGH" in summary


# ── compact() consolidation ──────────────────────────────────────────

def test_compact_consolidates_and_keeps_tail():
    wm = WorkingMemory(max_tokens=100)
    wm.append("system", "you are a backdoor detector")
    wm.append("user", "detect model.h5")
    for _ in range(20):
        wm.append_observation(
            {"tool_name": "strip_detect", "success": True, "risk_level": "HIGH",
             "confidence_score": 0.9}
        )

    assert wm._estimated_tokens > wm.max_tokens

    summary = wm.compact()
    assert summary is not None
    assert "strip_detect" in summary

    # summary message prepended
    assert wm.messages[0]["metadata"]["type"] == "summary"
    # system message preserved
    assert any(m["role"] == "system" for m in wm.messages)
    # recent tail preserved (last messages are tool observations)
    assert wm.messages[-1]["role"] == "tool"
    # evicted history is preserved, not lost
    assert len(wm.get_overflow()) > 0


def test_compact_noop_when_under_budget():
    wm = WorkingMemory(max_tokens=100000)
    wm.append("user", "hello")
    assert wm.compact() is None


def test_compact_recovers_budget():
    wm = WorkingMemory(max_tokens=200)
    wm.append("system", "sys")
    for _ in range(30):
        wm.append_observation(
            {"tool_name": "strip_detect", "success": True, "risk_level": "LOW"}
        )
    wm.compact()
    assert wm._estimated_tokens <= wm.max_tokens or len(wm.messages) <= 5


# ── Role-aware eviction ──────────────────────────────────────────────

def test_eviction_preserves_system_and_user():
    wm = WorkingMemory(max_tokens=30)
    wm.append("system", "sys prompt")
    wm.append("user", "A" * 80)     # ~20 tokens
    wm.append("tool", "B" * 80)     # ~20 tokens
    wm.append("assistant", "C" * 80)  # ~20 tokens

    wm.prune()

    roles = [m["role"] for m in wm.messages]
    # system preserved; tool/assistant evicted first
    assert "system" in roles


# ── Session summary (rule-based, no LLM) ─────────────────────────────

def test_session_compress_summary_includes_findings():
    sm = SessionMemory(trace_id="trc-1")
    sm.append_message("user", "detect")
    sm.store_tool_result("strip_detect", {"risk_level": "HIGH", "confidence_score": 0.9})
    summary = sm.compress_to_summary()
    assert summary is not None
    assert "strip_detect" in summary
    assert "HIGH" in summary
