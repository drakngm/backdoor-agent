"""
Dispatcher: Unified entry point for Agent Mode and Workflow Mode.

Routes incoming requests to the correct execution mode:
  - mode="agent"    → AgentLoop.run()
  - mode="workflow" → WorkflowExecutor with Planner strategy

Both modes share the same ToolRegistry.
"""

from typing import Any, Optional

from app.core.logging import get_logger
from app.core.trace import generate_trace_id
from app.agents.agent_loop import AgentLoop
from app.workflow.planner import Planner
from app.workflow.executor import WorkflowExecutor
from app.tools.registry import get_tool_registry

logger = get_logger(__name__)


class Dispatcher:
    """
    Routes execution requests to the appropriate mode.

    Usage:
        disp = Dispatcher()
        result = await disp.dispatch(mode="agent", input={"message": "detect model.h5"})
        result = await disp.dispatch(mode="workflow", input={"strategy": "deep_scan", "model_path": "model.h5"})
    """

    def __init__(self):
        self.registry = get_tool_registry()
        self.agent = AgentLoop()
        self.planner = Planner()
        self.executor = WorkflowExecutor(self.registry)

    async def dispatch(self, mode: str, input_data: dict[str, Any], trace_id: Optional[str] = None) -> dict[str, Any]:
        """
        Route to Agent or Workflow mode.

        Args:
            mode: "agent" or "workflow"
            input_data:
                For agent: {"message": str}
                For workflow: {"strategy": str, "model_path": str, ...}
            trace_id: Optional trace ID.

        Returns:
            Dict with trace_id, status, spans, mode, result.
        """
        trace_id = trace_id or generate_trace_id()

        if mode == "agent":
            return await self._run_agent(input_data, trace_id)
        elif mode == "workflow":
            return await self._run_workflow(input_data, trace_id)
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'agent' or 'workflow'.")

    async def _run_agent(self, input_data: dict[str, Any], trace_id: str) -> dict[str, Any]:
        """Execute Agent Mode."""
        message = input_data.get("message", "")
        if not message:
            raise ValueError("Agent mode requires 'message' in input_data")

        logger.info(f"Dispatcher → Agent Mode: {message[:80]}")
        trace = await self.agent.run(user_input=message, trace_id=trace_id)

        final_llm = None
        for span in trace.get_linear_chain():
            if span.span_type.value == "llm_call" and span.output:
                resp = span.output
                if resp.get("is_final"):
                    final_llm = resp.get("final_answer")
                    break

        return {
            "trace_id": trace.trace_id,
            "mode": "agent",
            "status": trace.status.value,
            "total_duration_ms": trace.total_duration_ms,
            "spans": trace.get_linear_chain(),
            "critical_path": trace.get_critical_path(),
            "mermaid": trace.to_mermaid(),
            "final_answer": final_llm,
        }

    async def _run_workflow(self, input_data: dict[str, Any], trace_id: str) -> dict[str, Any]:
        """Execute Workflow Mode."""
        strategy_name = input_data.get("strategy", "fast_scan")
        model_path = input_data.get("model_path", "model.h5")

        logger.info(f"Dispatcher → Workflow Mode: strategy={strategy_name}, model={model_path}")
        trace = await self.executor.execute(strategy_name=strategy_name, trace_id=trace_id, model_path=model_path)

        return {
            "trace_id": trace.trace_id,
            "mode": "workflow",
            "strategy": strategy_name,
            "status": trace.status.value,
            "total_duration_ms": trace.total_duration_ms,
            "spans": trace.get_linear_chain(),
            "span_tree": trace.get_span_tree(),
            "critical_path": trace.get_critical_path(),
            "mermaid": trace.to_mermaid(),
        }