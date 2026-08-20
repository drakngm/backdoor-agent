"""Tests for TaskGraph and Planner."""

import pytest
from app.workflow.task_graph import TaskGraph
from app.workflow.planner import Planner
from app.tools.registry import ToolRegistry
from app.tools.mock_strip import MockSTRIPDetector


def test_task_graph_simple():
    graph = TaskGraph()
    t1 = graph.add_task("tool_a", {"x": 1})
    t2 = graph.add_task("tool_b", {"y": 2}, depends_on=[t1])
    assert len(graph) == 2
    assert not graph.has_cycle()


def test_task_graph_no_cycle():
    graph = TaskGraph()
    t1 = graph.add_task("a")
    t2 = graph.add_task("b")
    t3 = graph.add_task("c", depends_on=[t1, t2])
    assert not graph.has_cycle()


def test_task_graph_topological_sort():
    graph = TaskGraph()
    a = graph.add_task("a")
    b = graph.add_task("b", depends_on=[a])
    c = graph.add_task("c", depends_on=[a])
    d = graph.add_task("d", depends_on=[b, c])
    order = graph.topological_sort()
    assert order.index(a) < order.index(b)
    assert order.index(a) < order.index(c)
    assert order.index(b) < order.index(d)
    assert order.index(c) < order.index(d)


def test_task_graph_tiers():
    graph = TaskGraph()
    a = graph.add_task("a")
    b = graph.add_task("b", depends_on=[a])
    c = graph.add_task("c", depends_on=[a])
    d = graph.add_task("d", depends_on=[b, c])
    tiers = graph.topological_tiers()
    assert len(tiers) == 3
    assert a in tiers[0]
    assert b in tiers[1] and c in tiers[1]
    assert d in tiers[2]


def test_planner_list_strategies():
    planner = Planner()
    strategies = planner.list_strategies()
    assert len(strategies) == 3
    names = [s["name"] for s in strategies]
    assert "fast_scan" in names
    assert "deep_scan" in names
    assert "forensic_scan" in names