"""Tests for Memory subsystem."""

import pytest
from app.memory.working_memory import WorkingMemory
from app.memory.session_memory import SessionMemory
from app.memory.knowledge_memory import KnowledgeMemory
from app.memory.manager import ContextManager


def test_working_memory_append():
    wm = WorkingMemory(max_tokens=10000)
    wm.append("user", "Hello")
    wm.append("assistant", "Hi there")
    assert len(wm.messages) == 2
    assert wm.messages[0]["role"] == "user"


def test_working_memory_prune():
    wm = WorkingMemory(max_tokens=5)  # Very small limit
    wm.append("user", "A" * 100)
    assert wm._estimated_tokens <= 5 or len(wm.messages) <= 1


def test_session_memory():
    sm = SessionMemory(trace_id="test")
    sm.append_message("user", "detect")
    sm.store_tool_result("strip", {"result": "ok"})
    assert len(sm.messages) == 1
    assert sm.get_tool_result("strip") == {"result": "ok"}
    assert sm.compress_to_summary() is not None


def test_knowledge_memory_search():
    km = KnowledgeMemory()
    results = km.search("STRIP detection", top_k=2)
    assert len(results) >= 1
    assert any("STRIP" in r["title"] for r in results)


def test_knowledge_memory_by_tag():
    km = KnowledgeMemory()
    docs = km.get_by_tag("deep_scan")
    assert len(docs) >= 1


def test_context_manager_search():
    ctx = ContextManager()
    ctx.init_session("test-001")
    ctx.add_user_message("detect model.h5")
    ctx.working.store("cached_key", "cached_value")
    result = ctx.search("cached_key")
    assert result == "cached_value"


def test_context_manager_knowledge_fallback():
    ctx = ContextManager()
    ctx.init_session("test-002")
    result = ctx.search("backdoor detection")
    assert result is not None
    assert isinstance(result, list)