"""
WorkflowExecutor: Executes a TaskGraph DAG by calling tools via ToolRegistry.

Supports:
  - Topological tier parallel execution (tasks in same tier run concurrently)
  - Executing an arbitrary (dynamically built) TaskGraph via `execute_graph`
  - Incremental execution with a result cache (for Hybrid Agent scheduling)
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
from app.core.execution_trace import ExecutionTrace, SpanType
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
        trace = ExecutionTrace(trace_id=trace_id)

        graph = self.planner.plan(strategy_name, self.registry, trace_id=trace_id, **kwargs)
        await self.execute_graph(graph, trace_id=trace_id, trace=trace)
        trace.finalize()
        return trace

    async def execute_graph(
        self,
        graph: TaskGraph,
        trace_id: Optional[str] = None,
        trace: Optional[ExecutionTrace] = None,
        cache: Optional[dict[str, dict[str, Any]]] = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Execute an arbitrary (dynamically built) TaskGraph.

        Args:
            graph: The DAG to execute.
            trace_id: Optional trace ID (generated if not provided).
            trace: Optional shared ExecutionTrace to write spans into.
            cache: Optional dict mapping task_id → output dict for nodes already
                executed (skipped, not re-run). Enables incremental scheduling by
                the Hybrid Agent.

        Returns:
            dict mapping task_id → tool output dict.

        Raises:
            WorkflowExecutionError: If any task fails.
        """
        trace_id = trace_id or generate_trace_id()
        trace = trace or ExecutionTrace(trace_id=trace_id)
        trace_logger = inject_trace_id(logger, trace_id)
        cache = cache or {}

        tiers = graph.topological_tiers()
        trace_logger.info(f"Executing DAG: {len(tiers)} tiers, {len(graph)} tasks")

        task_outputs: dict[str, dict[str, Any]] = dict(cache)

        for tier_idx, tier_task_ids in enumerate(tiers):
            # Skip cached nodes (already executed in a prior iteration).
            pending = [tid for tid in tier_task_ids if tid not in cache]
            if not pending:
                continue

            trace_logger.info(f"Executing tier {tier_idx}: {pending}")

            async def execute_task(tid: str) -> tuple[str, Optional[dict], Optional[str]]:
                task = graph.get_task(tid)
                span = trace.create_span(
                    name=f"task:{task.tool_name}",
                    span_type=SpanType.WORKFLOW_STEP,
                    input_data=task.params,
                )
                span.start()

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

            results = await asyncio.gather(
                *[execute_task(tid) for tid in pending],
                return_exceptions=False,
            )

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

        trace_logger.info(f"DAG execution finished: tasks_completed={len(task_outputs)}")
        return task_outputs
