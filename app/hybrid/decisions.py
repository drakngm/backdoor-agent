"""
Decision & plan models for the Hybrid Agent (Agent Loop + DAG Workflow).

A `DetectionStep` is one atomic decision: run a tool with params, depending on
prior steps. A `DetectionPlan` collects all steps made so far and can be
compiled into a deterministic TaskGraph (see compiler.py).

This realizes HA-4 (reproducibility): the plan is a serializable "decision
snapshot" that fully determines the DAG topology.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.hybrid.model_analyzer import ModelMetadata


class DetectionStep(BaseModel):
    """One agent decision: a tool invocation with dependencies."""

    step_id: str
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    reasoning: str = ""


class DetectionPlan(BaseModel):
    """Accumulated decisions, compiled to a DAG for deterministic execution."""

    trace_id: str
    model_metadata: ModelMetadata
    steps: list[DetectionStep] = Field(default_factory=list)

    model_config = {"protected_namespaces": ()}

    def add_step(self, step: DetectionStep) -> None:
        self.steps.append(step)

    def get_step(self, step_id: str) -> Optional[DetectionStep]:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def snapshot(self) -> dict[str, Any]:
        """Serializable decision snapshot (drives reproducibility)."""
        return self.model_dump()


class Decision(BaseModel):
    """
    Output of the decision engine for one iteration.

    Either `is_final` (with `final_answer`/`verdict`/`confidence`) or a `step`
    to execute next.
    """

    is_final: bool = False
    step: Optional[DetectionStep] = None
    final_answer: Optional[str] = None
    verdict: Optional[str] = None
    confidence: float = 0.0
