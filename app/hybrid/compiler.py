"""
DecisionCompiler: compiles a DetectionPlan (agent decisions) into a TaskGraph DAG.

Each DetectionStep becomes one DAG node (task); `depends_on` becomes graph edges.
This is the bridge that turns Agent decisions into deterministic, executable
DAG topology (HA-3).
"""

from app.hybrid.decisions import DetectionPlan
from app.workflow.task_graph import TaskGraph


class DecisionCompiler:
    """Compiles a DetectionPlan into an executable TaskGraph."""

    def compile(self, plan: DetectionPlan) -> TaskGraph:
        graph = TaskGraph()
        for step in plan.steps:
            graph.add_task(
                tool_name=step.tool_name,
                params=dict(step.params),
                depends_on=list(step.depends_on),
                task_id=step.step_id,
            )
        return graph
