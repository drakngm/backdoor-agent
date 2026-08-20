"""
TaskGraph: Simple DAG structure for Workflow Mode.

Represents a directed acyclic graph of tasks with dependencies.
Supports:
  - Add tasks with dependency edges
  - Topological sort (Kahn's algorithm)
  - Cycle detection
  - Tiered grouping for parallel execution
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.exceptions import TaskGraphError
from app.core.logging import get_logger

logger = get_logger(__name__)


class Task(BaseModel):
    """A single task node in the DAG."""

    task_id: str
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: str = "pending"  # pending, running, success, failed

    def __hash__(self):
        return hash(self.task_id)


class TaskGraph:
    """
    Directed Acyclic Graph of tasks.

    Usage:
        graph = TaskGraph()
        t1 = graph.add_task("model_loader", {"model_path": "model.h5"})
        t2 = graph.add_task("strip_detect", {}, depends_on=[t1])
        t3 = graph.add_task("report", {}, depends_on=[t2])

        async for tier in graph.topological_tiers():
            await execute_tier(tier)  # tasks in same tier can run in parallel
    """

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self._counter = 0

    def add_task(
        self,
        tool_name: str,
        params: Optional[dict[str, Any]] = None,
        depends_on: Optional[list[str]] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Add a task to the DAG.

        Args:
            tool_name: Tool to call (must be in ToolRegistry).
            params: Parameters passed to the tool.
            depends_on: List of task_ids this task depends on.
            task_id: Optional custom ID. Auto-generated if not provided.

        Returns:
            The task_id of the newly created task.

        Raises:
            TaskGraphError: If a dependency refers to an unknown task.
        """
        task_id = task_id or f"{tool_name}_{self._counter}"
        self._counter += 1
        depends_on = depends_on or []

        # Validate that all dependencies refer to known tasks
        for dep_id in depends_on:
            if dep_id not in self.tasks:
                raise TaskGraphError(
                    message=f"Dependency '{dep_id}' not found in graph for task '{task_id}'",
                    details={"task_id": task_id, "missing_dep": dep_id, "existing": list(self.tasks.keys())},
                )

        task = Task(
            task_id=task_id,
            tool_name=tool_name,
            params=params or {},
            depends_on=depends_on,
        )
        self.tasks[task_id] = task
        logger.debug(f"Task added: {task_id} (tool={tool_name}, depends_on={depends_on})")
        return task_id

    def has_cycle(self) -> bool:
        """
        Check if the DAG contains a cycle using DFS with colors.

        Returns:
            True if a cycle is detected.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {tid: WHITE for tid in self.tasks}

        def dfs(tid: str) -> bool:
            color[tid] = GRAY
            for dep in self.tasks[tid].depends_on:
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    return True  # Back edge → cycle
                if color[dep] == WHITE:
                    if dfs(dep):
                        return True
            color[tid] = BLACK
            return False

        for tid in self.tasks:
            if color[tid] == WHITE:
                if dfs(tid):
                    return True
        return False

    def topological_sort(self) -> list[str]:
        """
        Return task IDs in topological order (Kahn's algorithm).

        Returns:
            List of task_ids in execution order.

        Raises:
            TaskGraphError: If a cycle is detected.
        """
        if self.has_cycle():
            raise TaskGraphError(
                message="TaskGraph contains a cycle",
                details={"tasks": list(self.tasks.keys())},
            )

        in_degree: dict[str, int] = {tid: 0 for tid in self.tasks}
        for task in self.tasks.values():
            for dep in task.depends_on:
                if dep in in_degree:
                    in_degree[task.task_id] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            tid = queue.pop(0)
            result.append(tid)
            # Decrease in-degree of tasks that depend on this one
            for task in self.tasks.values():
                if tid in task.depends_on:
                    in_degree[task.task_id] -= 1
                    if in_degree[task.task_id] == 0:
                        queue.append(task.task_id)

        if len(result) != len(self.tasks):
            raise TaskGraphError(
                message="TaskGraph has unresolved dependencies",
                details={"sorted": result, "total": len(self.tasks)},
            )

        return result

    def topological_tiers(self) -> list[list[str]]:
        """
        Group tasks into tiers where all tasks in a tier can run in parallel.

        Returns:
            List of tiers, each tier is a list of task_ids.
            Tier 0 has no dependencies, Tier 1 depends only on Tier 0, etc.
        """
        sorted_ids = self.topological_sort()
        tiers: list[list[str]] = []
        current_tier: list[str] = []
        completed: set[str] = set()

        for tid in sorted_ids:
            task = self.tasks[tid]
            deps = set(task.depends_on)

            # If all deps are in previously completed tiers, add to current tier
            if deps.issubset(completed):
                current_tier.append(tid)
            else:
                # Flush current tier
                if current_tier:
                    tiers.append(current_tier)
                    completed.update(current_tier)
                # Start new tier
                current_tier = [tid]

        if current_tier:
            tiers.append(current_tier)

        return tiers

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID."""
        if task_id not in self.tasks:
            raise TaskGraphError(
                message=f"Task '{task_id}' not found in graph",
                details={"task_id": task_id, "existing": list(self.tasks.keys())},
            )
        return self.tasks[task_id]

    def __len__(self) -> int:
        return len(self.tasks)