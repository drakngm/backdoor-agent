"""
HybridAgent: orchestrates the Agent Loop (reasoning) + DAG Workflow (execution).

The collaborative loop:

    1. analyze model metadata (architecture)
    2. decision engine chooses the next tool + params + dependencies
    3. decision is compiled into a DAG node (DecisionCompiler)
    4. the DAG executor deterministically runs it (WorkflowExecutor.execute_graph)
    5. the result feeds back into the decision engine
    6. repeat until a final verdict; then produce a report

The accumulated DetectionPlan is a reproducible "decision snapshot": the same
metadata + the same (deterministic) tool results yield the same DAG topology.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.hybrid.decisions import Decision, DetectionPlan
from app.hybrid.model_analyzer import ModelAnalyzer, ModelMetadata
from app.hybrid.decision_engine import DecisionEngine
from app.hybrid.compiler import DecisionCompiler
from app.workflow.executor import WorkflowExecutor
from app.tools.registry import get_tool_registry
from app.core.trace import generate_trace_id
from app.core.execution_trace import ExecutionTrace, EventType
from app.core.logging import get_logger, inject_trace_id

logger = get_logger(__name__)


def _as_str(value: Any) -> Any:
    return getattr(value, "value", value)


class HybridResult(BaseModel):
    """Aggregated result of a hybrid detection run."""

    trace_id: str
    status: str
    total_duration_ms: Optional[float] = None
    verdict: Optional[str] = None
    confidence: float = 0.0
    final_answer: Optional[str] = None
    model_metadata: ModelMetadata
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] = Field(default_factory=dict)
    mermaid: str = ""
    critical_path: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"protected_namespaces": ()}


class HybridAgent:
    """
    Hybrid Agent: Agent Loop (high-level decisions) + DAG Workflow (deterministic
    execution), connected via the decision compiler.
    """

    def __init__(
        self,
        analyzer: Optional[ModelAnalyzer] = None,
        engine: Optional[DecisionEngine] = None,
        compiler: Optional[DecisionCompiler] = None,
        executor: Optional[WorkflowExecutor] = None,
    ):
        self.analyzer = analyzer or ModelAnalyzer()
        self.engine = engine or DecisionEngine()
        self.compiler = compiler or DecisionCompiler()
        self.executor = executor or WorkflowExecutor(get_tool_registry())
        self.max_steps = getattr(self.engine, "max_steps", 10)

    async def run(
        self,
        task: str,
        model_path: str,
        trace_id: Optional[str] = None,
    ) -> HybridResult:
        """
        Run a hybrid detection task.

        Args:
            task: The detection task description (e.g. "检测 ResNet-18 是否存在后门").
            model_path: Path to the model to analyze.
            trace_id: Optional trace ID.

        Returns:
            HybridResult with verdict, decision chain, tool results, and report.
        """
        trace_id = trace_id or generate_trace_id()
        trace_logger = inject_trace_id(logger, trace_id)
        trace = ExecutionTrace(trace_id=trace_id)

        metadata = self.analyzer.analyze(model_path)
        plan = DetectionPlan(trace_id=trace_id, model_metadata=metadata)
        results: dict[str, dict[str, Any]] = {}

        trace_logger.info(f"Hybrid agent started: task='{task[:60]}' model='{model_path}'")

        final_decision: Optional[Decision] = None
        for iteration in range(self.max_steps):
            decision = self.engine.decide(metadata, results, plan)

            if decision.is_final:
                final_decision = decision
                break

            step = decision.step
            plan.add_step(step)
            trace.add_event(
                EventType.LLM_RESPONSE,
                message=step.reasoning,
                metadata={"step_id": step.step_id, "tool": step.tool_name},
            )

            # Compile the (growing) plan into a DAG and execute deterministically.
            graph = self.compiler.compile(plan)
            new_outputs = await self.executor.execute_graph(
                graph, trace_id=trace_id, trace=trace, cache=results
            )
            results.update(new_outputs)

        if final_decision is None:
            final_decision = Decision(
                is_final=True,
                verdict="inconclusive",
                final_answer=f"达到最大决策步数（{self.max_steps}），终止",
            )

        report = self._build_report(metadata, final_decision, plan, results)
        trace.finalize()

        return HybridResult(
            trace_id=trace_id,
            status=trace.status.value,
            total_duration_ms=trace.total_duration_ms,
            verdict=final_decision.verdict,
            confidence=final_decision.confidence,
            final_answer=final_decision.final_answer,
            model_metadata=metadata,
            decisions=[s.model_dump() for s in plan.steps],
            tool_results=[
                {
                    "step_id": sid,
                    "tool": r.get("tool_name"),
                    "success": r.get("success"),
                    "risk_level": _as_str(r.get("risk_level")),
                    "confidence": r.get("confidence_score"),
                    "is_backdoor": (r.get("data") or {}).get("is_backdoor"),
                }
                for sid, r in results.items()
            ],
            report=report,
            mermaid=trace.to_mermaid(),
            critical_path=trace.get_critical_path(),
        )

    def _build_report(
        self,
        metadata: ModelMetadata,
        decision: Decision,
        plan: DetectionPlan,
        results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "report_id": f"report-{plan.trace_id}",
            "trace_id": plan.trace_id,
            "model_path": metadata.path,
            "architecture": metadata.architecture,
            "scan_strategy": "hybrid_agent",
            "verdict": decision.verdict,
            "confidence": decision.confidence,
            "final_answer": decision.final_answer,
            "steps_executed": len(plan.steps),
            "tools_executed": len(results),
            "decision_snapshot": plan.snapshot(),
        }
