"""
WorkflowExecutor: Executes a TaskGraph DAG by calling tools via ToolRegistry.

Supports:
  - Topological tier parallel execution (tasks in same tier run concurrently)
  - Full trace integration via ExecutionTrace
  - Tool call routing via ToolRouter
"""

import asyncio
from typing import Any, Optional

from app.workflow.task_graph import TaskGraph, Task
from app.workflow.planner import Planner
from app.tools.registry import ToolRegistry, get_tool_registry
from app.agents.tool_router import ToolRouter, ToolCallRequest
from app.core.trace import generate_trace_id
from app.core.execution_trace import ExecutionTrace, SpanType, SpanStatus
from app.core.logging import get_logger, inject_trace_id
from app.core.exceptions import WorkflowExecutionError

logger = get_logger(__name__)


class WorkflowExecutor:
    """
    Executes a TaskGraph DAG.

    Usage:
        executor = WorkflowExecutor(registry)
        trace = await executor.execute(strategy_name="deep_scan", model_path="model.h5")
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_tool_registry()
        self.router = ToolRouter(self.registry)
        self.planner = Planner()

    async def execute(
        self,
        strategy_name: str = "fast_scan",
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ExecutionTrace:
        """
        Plan + execute a workflow using the specified strategy.

        Args:
            strategy_name: One of "fast_scan", "deep_scan", "forensic_scan".
            trace_id: Optional trace ID.
            **kwargs: Forwarded to strategy.build_task_graph() (e.g., model_path).

        Returns:
            ExecutionTrace with full span tree.

        Raises:
            WorkflowExecutionError: If any task fails.
        """
        trace_id = trace_id or generate_trace_id()
        trace_logger = inject_trace_id(logger, trace_id)
        trace = ExecutionTrace(trace_id=trace_id)

        trace_logger.info(f"Workflow execution started: strategy={strategy_name}")

        # Step 1: Plan
        graph = self.planner.plan(strategy_name, self.registry, trace_id=trace_id, **kwargs)
        tiers = graph.topological_tiers()
        trace_logger.info(f"Workflow plan: {len(tiers)} tiers, {len(graph)} tasks")

        # Step 2: Execute tier by tier
        task_outputs: dict[str, dict[str, Any]] = {}

        for tier_idx, tier_task_ids in enumerate(tiers):
            trace_logger.info(f"Executing tier {tier_idx}: {tier_task_ids}")

            async def execute_task(tid: str) -> tuple[str, Optional[dict], Optional[str]]:
                task = graph.get_task(tid)
                span = trace.create_span(
                    name=f"task:{task.tool_name}",
                    span_type=SpanType.WORKFLOW_STEP,
                    input_data=task.params,
                )
                span.start()

                # Build tool call request with trace_id
                params = dict(task.params)
                params["trace_id"] = trace_id

                try:
                    result = await self.router.route(
                        ToolCallRequest(tool_name=task.tool_name, input_data=params)
                    )
                    span.finish(output=result.model_dump())
                    task.status = "success"
                    return tid, result.model_dump(), None
                except Exception as e:
                    span.fail(str(e))
                    task.status = "failed"
                    return tid, None, str(e)

            # Run all tasks in current tier concurrently
            results = await asyncio.gather(
                *[execute_task(tid) for tid in tier_task_ids],
                return_exceptions=False,
            )

            # Check for failures
            failed_tasks = []
            for tid, output, error in results:
                if error:
                    failed_tasks.append((tid, error))
                else:
                    task_outputs[tid] = output

            if failed_tasks:
                for tid, err in failed_tasks:
                    trace_logger.error(f"Task {tid} failed: {err}")
                raise WorkflowExecutionError(
                    message=f"Workflow failed: {len(failed_tasks)} task(s) in tier {tier_idx} failed",
                    trace_id=trace_id,
                    details={"failed_tasks": [{"task_id": t, "error": e} for t, e in failed_tasks]},
                )

        # Step 3: Finalize trace
        trace.finalize()
        trace_logger.info(
            f"Workflow finished: status={trace.status.value}, "
            f"duration={trace.total_duration_ms:.0f}ms, "
            f"tasks_completed={len(task_outputs)}"
        )

        return trace