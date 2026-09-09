"""Deterministic mock data generators for the BFF dashboard layer.

Used when the core backend is unreachable, so the frontend always has
something meaningful to render (and demos stay offline-friendly).
"""

import math
import random
from datetime import datetime, timedelta, timezone

random.seed(20260825)


def _series(n: int, base: float, amp: float, period: float = 0.0) -> list[float]:
    out = []
    v = base
    for i in range(n):
        v = max(0.0, v + random.uniform(-amp / 2, amp / 2) + (math.sin((i + period) / 3) * amp * 0.18))
        out.append(round(v, 1))
    return out


def health() -> dict:
    return {
        "status": "operational",
        "app": "AI Backdoor Detection & Defense Agent System",
        "version": "1.4.0",
        "uptime_seconds": 38642,
        "tools": ["STRIP", "NeuralCleanse", "ActivationClustering"],
    }


def metrics() -> dict:
    return {
        "threat_level": "LOW",
        "detection_confidence": 98.7,
        "active_agents": 6,
        "running_workflows": 2,
        "detection_latency_ms": 142,
        "detections_last_24h": 3,
        "scan_strategy": "deep_scan",
    }


def overview() -> dict:
    return {
        "backdoors_detected": 24,
        "backdoors_trend": _series(18, 24, 7),
        "clean_models": 1284,
        "clean_models_trend": _series(18, 1284, 46),
        "models_analyzed": 8942,
        "models_analyzed_trend": _series(18, 8942, 130),
    }


def dag() -> dict:
    return {
        "id": "dag-live-001",
        "nodes": [
            {"id": "analyzer", "label": "Model Analyzer", "sub": "metadata · conv", "group": "analyze", "state": "completed"},
            {"id": "strip", "label": "STRIP", "sub": "input perturbation", "group": "detect", "state": "running"},
            {"id": "cleanse", "label": "Neural Cleanse", "sub": "trojan trigger", "group": "detect", "state": "waiting"},
            {"id": "cluster", "label": "Activation Clustering", "sub": "feature space", "group": "detect", "state": "waiting"},
            {"id": "llm", "label": "LLM Analysis", "sub": "decision · CoT", "group": "reason", "state": "waiting"},
            {"id": "report", "label": "Report Generator", "sub": "artifact emit", "group": "output", "state": "waiting"},
        ],
        "edges": [
            {"source": "analyzer", "target": "strip"},
            {"source": "strip", "target": "cleanse", "label": "feeds"},
            {"source": "strip", "target": "cluster", "label": "feeds"},
            {"source": "cleanse", "target": "llm"},
            {"source": "cluster", "target": "llm"},
            {"source": "llm", "target": "report"},
        ],
    }


def timeline(points: int = 40) -> list[dict]:
    now = datetime.now(timezone.utc)
    out = []
    for i in range(points):
        ts = now - timedelta(minutes=15 * (points - i))
        out.append(
            {
                "t": ts.isoformat(),
                "strip": round(random.uniform(2, 14), 1),
                "neural_cleanse": round(random.uniform(1, 10), 1),
                "activation_clustering": round(random.uniform(1, 9), 1),
                "overall": round(random.uniform(4, 22), 1),
            }
        )
    return out


def detectors() -> list[dict]:
    return [
        {"name": "strp", "display": "STRIP", "description": "Input perturbation to detect trigger-reactive neurons.", "status": "active", "last_run_ms": 142, "detections": 9, "precision": 0.99},
        {"name": "ncln", "display": "Neural Cleanse", "description": "Reverse-engineers trojan triggers via optimization.", "status": "idle", "last_run_ms": 2260, "detections": 11, "precision": 0.97},
        {"name": "actcl", "display": "Activation Clustering", "description": "Clusters penultimate-layer activations for poisoned behavior.", "status": "idle", "last_run_ms": 840, "detections": 4, "precision": 0.95},
    ]


def memory() -> dict:
    return {
        "episodic": {"entries": 1284, "size_bytes": 18_874_331},
        "semantic": {"entries": 342, "dims": 1536},
        "procedural": {"rules": 47},
        "last_consolidation": (datetime.now(timezone.utc) - timedelta(minutes=4)).isoformat(),
    }


def traces() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {"trace_id": "trc_9f2a11c4", "mode": "hybrid", "status": "completed", "started_at": now.isoformat(), "duration_ms": 3872, "spans": 24},
        {"trace_id": "trc_7c0e8b21", "mode": "workflow", "status": "completed", "started_at": (now - timedelta(seconds=60)).isoformat(), "duration_ms": 2410, "spans": 16},
        {"trace_id": "trc_5b31a9d0", "mode": "agent", "status": "running", "started_at": (now - timedelta(seconds=3)).isoformat(), "duration_ms": 812, "spans": 5},
    ]


def logs() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {"time": now.isoformat(), "level": "INFO", "logger": "core.trace", "message": "Span completed tool=STRIP status=passed duration_ms=142", "trace_id": "trc_9f2a11c4"},
        {"time": (now - timedelta(seconds=8)).isoformat(), "level": "INFO", "logger": "hybrid.agent", "message": "HybridAgent decision gate → proceed to DAG workflow", "trace_id": "trc_9f2a11c4"},
        {"time": (now - timedelta(seconds=16)).isoformat(), "level": "WARN", "logger": "security.neural_cleanse", "message": "Anomaly score above threshold: 0.87 > 0.6", "trace_id": "trc_7c0e8b21"},
        {"time": (now - timedelta(seconds=30)).isoformat(), "level": "INFO", "logger": "app", "message": "Tools registered: STRIP, NeuralCleanse, ActivationClustering", "trace_id": None},
        {"time": (now - timedelta(seconds=45)).isoformat(), "level": "DEBUG", "logger": "memory.semantic", "message": "Vector store query top-k=5 returned 342 candidates", "trace_id": "trc_5b31a9d0"},
    ]


def threats() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {"id": "thr_8821", "time": now.isoformat(), "severity": "high", "source": "model_zoo/vgg16_bdoor.h5", "summary": "Trigger pattern detected in conv4_2 feature space.", "detector": "Neural Cleanse"},
        {"id": "thr_8817", "time": (now - timedelta(minutes=8)).isoformat(), "severity": "medium", "source": "ft/resnet50_xfer.h5", "summary": "Class cluster deviation flagged across 3 classes.", "detector": "Activation Clustering"},
        {"id": "thr_8792", "time": (now - timedelta(minutes=34)).isoformat(), "severity": "low", "source": "llm/embed_inject.pt", "summary": "High-entropy input layer sensitivity observed.", "detector": "STRIP"},
    ]


def resources() -> dict:
    return {"cpu": 34, "gpu": 62, "mem": 48, "gpu_name": "NVIDIA A100 · 40GB"}


_MOCK_EXECUTIONS = {
    "agent": {
        "mode": "agent",
        "status": "completed",
        "final_answer": "Symbolic pre-check passed. Routed model to scanning tools; STRIP clean, Neural Cleanse confidence 0.87.",
        "critical_path": ["llm_call", "tool_router", "STRIP", "final_llm"],
    },
    "workflow": {
        "mode": "workflow",
        "status": "completed",
        "final_answer": "Workflow executed: 16 spans, no blocking tasks; report artifact emitted.",
        "critical_path": ["planner", "task_graph", "STRIP", "cleanse", "report"],
    },
    "hybrid": {
        "mode": "hybrid",
        "status": "completed",
        "verdict": "CLEAN",
        "confidence": 98.1,
        "final_answer": "Model analyzed: no active backdoor found (confidence 98.1%).",
        "decisions": [
            "Decision 1: inspect model metadata → schedule STRIP scan",
            "Decision 2: cross-validate anomaly score 0.06 < 0.6 threshold",
            "Decision 3: verdict CLEAN → generate audit report",
        ],
        "tool_results": [
            {"tool": "STRIP", "done": True, "passed": True},
            {"tool": "NeuralCleanse", "done": True, "passed": True},
            {"tool": "ActivationClustering", "done": True, "passed": True},
        ],
        "critical_path": ["analyzer", "strip", "cleanse", "decision_engine", "report"],
    },
}


def execute(mode: str) -> dict:
    result = dict(_MOCK_EXECUTIONS[mode])
    result["trace_id"] = f"trc_{random.randbytes(4).hex()}"
    result["source"] = "mock"
    return result