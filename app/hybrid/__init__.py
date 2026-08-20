"""
Hybrid Agent package: Agent Loop (reasoning) + DAG Workflow (execution) bridge.

Components:
  - ModelAnalyzer   : infer model metadata (architecture)
  - DecisionEngine  : rule-based reasoning -> DetectionStep decisions
  - DecisionCompiler: DetectionPlan -> TaskGraph DAG
  - HybridAgent     : orchestrates decide -> compile -> execute -> repeat
"""

from app.hybrid.model_analyzer import ModelAnalyzer, ModelMetadata
from app.hybrid.decisions import DetectionStep, DetectionPlan, Decision
from app.hybrid.decision_engine import DecisionEngine
from app.hybrid.compiler import DecisionCompiler
from app.hybrid.hybrid_agent import HybridAgent, HybridResult

__all__ = [
    "ModelAnalyzer",
    "ModelMetadata",
    "DetectionStep",
    "DetectionPlan",
    "Decision",
    "DecisionEngine",
    "DecisionCompiler",
    "HybridAgent",
    "HybridResult",
]
