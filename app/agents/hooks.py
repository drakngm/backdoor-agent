"""
Hook System for Agent Runtime (Claude Code Harness style).

Adapted from Claude Code's hook model (PreToolUse / PostToolUse / Stop),
as taught in learn-claude-code s04_hooks:

  - PreToolUse : runs before a tool executes. A hook may DENY (block) the call
                 or rewrite its input (Claude Code `updatedInput` analog).
  - PostToolUse: runs after a tool returns. A hook may DENY (reject) the result,
                 transform it, or inject additional context (Claude Code
                 `additionalContext` analog).

Design contract:
  - A hook returns Optional[HookResult]. `None` => allow, no change.
  - HookResult carries {decision: allow|deny, reason, updated_input,
    updated_output, additional_context}.
  - HookManager aggregates all hooks for an event:
      * any DENY => overall DENY (first reason kept)
      * last non-None updated_input / updated_output wins
      * additional_context is concatenated

This realizes the resume's "Pre/Post Hook 控制逻辑（工具执行前后的
输入校验与结果验证）": PreToolUse = input validation, PostToolUse = result
verification.
"""

import re
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel

from app.core.logging import get_logger
from app.tools.schemas import ToolOutput, RiskLevel

logger = get_logger(__name__)


# ── Decision model ───────────────────────────────────────────────────

class HookDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class HookResult(BaseModel):
    """Outcome of a hook invocation (Claude Code permissionDecision analog)."""

    decision: HookDecision = HookDecision.ALLOW
    reason: str = ""
    updated_input: Optional[dict[str, Any]] = None
    updated_output: Optional[Any] = None
    additional_context: Optional[str] = None

    @classmethod
    def deny(cls, reason: str) -> "HookResult":
        return cls(decision=HookDecision.DENY, reason=reason)


# ── Hook type aliases ───────────────────────────────────────────────

BeforeToolHook = Callable[[str, dict[str, Any]], Optional[HookResult]]
AfterToolHook = Callable[[str, dict[str, Any], ToolOutput], Optional[HookResult]]
ErrorHook = Callable[[Exception, str, dict[str, Any]], None]
LoopHook = Callable[[int, dict[str, Any]], None]


# ── Hook manager ─────────────────────────────────────────────────────

class HookManager:
    """
    Manages hooks for the Agent Loop lifecycle.

    Events:
      before_tool (PreToolUse)  — input validation, input rewriting, blocking
      after_tool  (PostToolUse) — result verification, transform, context inject
      on_error                  — error fallback/alerting
      loop_start / loop_end     — per-iteration lifecycle
    """

    def __init__(self):
        self._before_tool_hooks: list[BeforeToolHook] = []
        self._after_tool_hooks: list[AfterToolHook] = []
        self._error_hooks: list[ErrorHook] = []
        self._loop_start_hooks: list[LoopHook] = []
        self._loop_end_hooks: list[LoopHook] = []
        self._enabled: bool = True

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    # ── Registration ─────────────────────────────────────────────

    def on_before_tool(self, hook: BeforeToolHook) -> BeforeToolHook:
        self._before_tool_hooks.append(hook)
        return hook

    def on_after_tool(self, hook: AfterToolHook) -> AfterToolHook:
        self._after_tool_hooks.append(hook)
        return hook

    def on_error(self, hook: ErrorHook) -> ErrorHook:
        self._error_hooks.append(hook)
        return hook

    def on_loop_start(self, hook: LoopHook) -> LoopHook:
        self._loop_start_hooks.append(hook)
        return hook

    def on_loop_end(self, hook: LoopHook) -> LoopHook:
        self._loop_end_hooks.append(hook)
        return hook

    # ── Fire hooks ───────────────────────────────────────────────

    async def fire_before_tool(self, tool_name: str, input_data: dict[str, Any]) -> HookResult:
        """Run all PreToolUse hooks; aggregate into a single HookResult."""
        result = HookResult()
        if not self._enabled:
            return result

        contexts: list[str] = []
        for hook in self._before_tool_hooks:
            try:
                r = hook(tool_name, input_data)
            except Exception as e:
                logger.warning(f"BeforeTool hook failed: {e}")
                continue
            if r is None:
                continue
            if r.decision == HookDecision.DENY and result.decision == HookDecision.ALLOW:
                result.decision = HookDecision.DENY
                result.reason = r.reason
            if r.updated_input is not None:
                result.updated_input = r.updated_input
            if r.additional_context:
                contexts.append(r.additional_context)

        if contexts:
            result.additional_context = "\n".join(contexts)
        return result

    async def fire_after_tool(
        self, tool_name: str, input_data: dict[str, Any], output: ToolOutput
    ) -> HookResult:
        """Run all PostToolUse hooks; aggregate into a single HookResult."""
        result = HookResult()
        if not self._enabled:
            return result

        contexts: list[str] = []
        for hook in self._after_tool_hooks:
            try:
                r = hook(tool_name, input_data, output)
            except Exception as e:
                logger.warning(f"AfterTool hook failed: {e}")
                continue
            if r is None:
                continue
            if r.decision == HookDecision.DENY and result.decision == HookDecision.ALLOW:
                result.decision = HookDecision.DENY
                result.reason = r.reason
            if r.updated_output is not None:
                result.updated_output = r.updated_output
            if r.additional_context:
                contexts.append(r.additional_context)

        if contexts:
            result.additional_context = "\n".join(contexts)
        return result

    async def fire_on_error(self, error: Exception, tool_name: str, input_data: dict[str, Any]) -> None:
        if not self._enabled:
            return
        for hook in self._error_hooks:
            try:
                hook(error, tool_name, input_data)
            except Exception as e:
                logger.warning(f"Error hook failed: {e}")

    async def fire_loop_start(self, iteration: int, context: dict[str, Any]) -> None:
        if not self._enabled:
            return
        for hook in self._loop_start_hooks:
            try:
                hook(iteration, context)
            except Exception as e:
                logger.warning(f"LoopStart hook failed: {e}")

    async def fire_loop_end(self, iteration: int, context: dict[str, Any]) -> None:
        if not self._enabled:
            return
        for hook in self._loop_end_hooks:
            try:
                hook(iteration, context)
            except Exception as e:
                logger.warning(f"LoopEnd hook failed: {e}")


# ── Built-in logging hooks ──────────────────────────────────────────

def default_before_tool_hook(tool_name: str, input_data: dict[str, Any]) -> Optional[HookResult]:
    """PreToolUse: log the call."""
    logger.info(f"[hook] BeforeTool: {tool_name}")
    return None


def default_after_tool_hook(
    tool_name: str, input_data: dict[str, Any], output: ToolOutput
) -> Optional[HookResult]:
    """PostToolUse: log the result status."""
    logger.info(f"[hook] AfterTool: {tool_name} success={getattr(output, 'success', False)}")
    return None


def default_error_hook(error: Exception, tool_name: str, input_data: dict[str, Any]) -> None:
    """Error: log the failure."""
    logger.error(f"[hook] Error in {tool_name}: {error}")


# ── Built-in validation hooks (PreToolUse: 输入校验) ─────────────────

_ABSOLUTE_PATH_RE = re.compile(r"^([A-Za-z]:[\\/]|[\\/])")


def _is_unsafe_path(path: str) -> bool:
    """True for null bytes, `..` traversal, or absolute/drive paths."""
    if not isinstance(path, str):
        return True
    if "\x00" in path:
        return True
    if ".." in re.split(r"[\\/]+", path):
        return True
    if _ABSOLUTE_PATH_RE.match(path):
        return True
    return False


def validate_input_hook(tool_name: str, input_data: dict[str, Any]) -> Optional[HookResult]:
    """PreToolUse: semantic input validation (required fields + value ranges)."""
    if not input_data.get("trace_id"):
        return HookResult.deny("missing required field: trace_id")

    model_path = input_data.get("model_path")
    if model_path is None or not str(model_path).strip():
        return HookResult.deny("missing required field: model_path")

    ranges: dict[str, tuple[Optional[float], Optional[float]]] = {
        "num_samples": (0, None),        # > 0
        "num_classes": (1, None),        # >= 1
        "n_clusters": (1, None),         # >= 1
        "optimization_steps": (0, None),  # >= 0
    }
    for field, (lo, hi) in ranges.items():
        value = input_data.get(field)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or value < lo or (hi is not None and value > hi):
            return HookResult.deny(f"invalid {field}: {value}")

    strength = input_data.get("perturbation_strength")
    if strength is not None and (
        not isinstance(strength, (int, float)) or not (0.0 <= float(strength) <= 1.0)
    ):
        return HookResult.deny(f"perturbation_strength out of [0,1]: {strength}")

    return None


def path_safety_hook(tool_name: str, input_data: dict[str, Any]) -> Optional[HookResult]:
    """PreToolUse: deny path traversal / absolute paths for file arguments."""
    for field in ("model_path",):
        value = input_data.get(field)
        if value is not None and _is_unsafe_path(str(value)):
            return HookResult.deny(f"unsafe {field}: {value}")
    return None


# ── Built-in verification hooks (PostToolUse: 结果验证) ──────────────

def verify_output_hook(
    tool_name: str, input_data: dict[str, Any], output: ToolOutput
) -> Optional[HookResult]:
    """PostToolUse: hard result verification (deny on invalid output)."""
    confidence = getattr(output, "confidence_score", None)
    if confidence is not None and not (0.0 <= float(confidence) <= 1.0):
        return HookResult.deny(f"confidence_score out of [0,1]: {confidence}")

    if not output.success and not output.error:
        return HookResult.deny("tool reported failure but no error message")

    for artifact in output.artifact or []:
        if artifact.hash is not None and not str(artifact.hash).startswith("sha256:"):
            return HookResult.deny(f"artifact '{artifact.name}' has malformed hash")

    return None


def result_consistency_hook(
    tool_name: str, input_data: dict[str, Any], output: ToolOutput
) -> Optional[HookResult]:
    """PostToolUse: soft cross-field consistency check (adds context, never denies)."""
    data = output.data or {}
    is_backdoor = data.get("is_backdoor")
    risk = output.risk_level

    if is_backdoor is True and risk == RiskLevel.LOW:
        return HookResult(additional_context=(
            f"[consistency] {tool_name}: data.is_backdoor=True but risk_level=LOW"
        ))
    if is_backdoor is False and risk == RiskLevel.HIGH:
        return HookResult(additional_context=(
            f"[consistency] {tool_name}: data.is_backdoor=False but risk_level=HIGH"
        ))
    return None


# ── Default hook wiring ─────────────────────────────────────────────

def register_default_hooks(hooks: HookManager) -> HookManager:
    """Register logging + validation + verification hooks on a HookManager."""
    # PreToolUse: log, then validate input, then path-safety
    hooks.on_before_tool(default_before_tool_hook)
    hooks.on_before_tool(validate_input_hook)
    hooks.on_before_tool(path_safety_hook)

    # PostToolUse: log, then verify result, then consistency check
    hooks.on_after_tool(default_after_tool_hook)
    hooks.on_after_tool(verify_output_hook)
    hooks.on_after_tool(result_consistency_hook)

    # Error
    hooks.on_error(default_error_hook)

    return hooks
