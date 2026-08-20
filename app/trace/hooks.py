"""
TraceRecorder: pre/post hooks that record Data Trace + Audit Trail.

Combines the four-level trace with the existing Pre/Post hook mechanism:
  - PreToolUse  hook -> record tool_start audit + input hash (pending)
  - PostToolUse hook -> record data-flow entry (input/output + hashes) + tool_end audit

The hooks conform to the HookManager signatures (return Optional[HookResult]),
so they can be registered alongside the validation hooks.
"""

from typing import Any, Optional

from app.agents.hooks import HookResult
from app.trace.models import stable_hash
from app.trace.trace import FourLevelTrace


class TraceRecorder:
    """Records L2 (data) + L4 (audit) traces via pre/post tool hooks."""

    def __init__(self, trace: FourLevelTrace):
        self.trace = trace
        self._pending: dict[str, tuple[dict[str, Any], str]] = {}

    def pre_tool_hook(self, tool_name: str, input_data: dict[str, Any]) -> Optional[HookResult]:
        input_hash = stable_hash(input_data)
        self._pending[tool_name] = (dict(input_data), input_hash)
        self.trace.record_audit(
            "tool_start",
            f"tool={tool_name}",
            {"tool": tool_name, "input_hash": input_hash},
        )
        return None  # allow (never blocks)

    def post_tool_hook(
        self, tool_name: str, input_data: dict[str, Any], output: Any
    ) -> Optional[HookResult]:
        input_data, input_hash = self._pending.pop(
            tool_name, (dict(input_data), stable_hash(input_data))
        )
        output_dict = output.model_dump() if hasattr(output, "model_dump") else dict(output)
        output_hash = stable_hash(output_dict)

        self.trace.record_data(
            step_id=tool_name,
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_dict,
        )
        self.trace.record_audit(
            "tool_end",
            f"tool={tool_name}",
            {"tool": tool_name, "output_hash": output_hash},
        )
        return None  # allow (never blocks)
