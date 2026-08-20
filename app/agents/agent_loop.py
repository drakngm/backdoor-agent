"""
AgentLoop: Core Agent Runtime (Claude Code Harness style).

Implements the LLM → Tool → Observation → Loop cycle.

The LLM is injected via the LLMClient abstraction (app.llm); it defaults to the
configured provider (mock by default) and can be swapped for OpenAI/Anthropic
without touching the loop logic.

The loop:
  1. Build prompt from WorkingMemory
  2. Call LLM → parse response (tool_call or final_answer)
  3. If tool_call: fire before_tool hooks → ToolRouter.route() → fire after_tool hooks
  4. Observation → append to WorkingMemory + SessionMemory
  5. Repeat until final_answer or max_iterations
"""

from typing import Any, Optional

from app.agents.tool_router import ToolRouter
from app.agents.hooks import HookManager, HookDecision, register_default_hooks
from app.tools.registry import get_tool_registry
from app.memory.manager import ContextManager
from app.core.config import get_config
from app.core.trace import generate_trace_id
from app.core.execution_trace import ExecutionTrace, SpanType, EventType
from app.core.logging import get_logger, inject_trace_id
from app.core.exceptions import AgentLoopTimeoutError, AgentError

from app.llm.base import LLMClient
from app.llm import create_llm_client
from app.llm.providers.mock import MockLLMClient

logger = get_logger(__name__)

# Backward-compatible alias: code/tests previously imported MockLLM here.
MockLLM = MockLLMClient


# ── Agent Loop ───────────────────────────────────────────────────────

class AgentLoop:
    """
    Core agent loop implementing the Claude Code Harness pattern.

    Usage:
        agent = AgentLoop()
        trace = await agent.run("Detect backdoors in model.h5")
        print(trace.to_mermaid())
    """

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        router: Optional[ToolRouter] = None,
        memory: Optional[ContextManager] = None,
        hooks: Optional[HookManager] = None,
    ):
        self.llm = llm or create_llm_client()
        self.router = router or ToolRouter(get_tool_registry())
        self.memory = memory or ContextManager()
        self.hooks = hooks or HookManager()

        # Register default hooks (logging + input validation + result verification)
        register_default_hooks(self.hooks)

        self._max_iterations = get_config().agent_max_iterations
        self.llm.reset()

    async def run(self, user_input: str, trace_id: Optional[str] = None) -> ExecutionTrace:
        """
        Execute the agent loop.

        Args:
            user_input: The user's message/request.
            trace_id: Optional trace ID. Generated if not provided.

        Returns:
            ExecutionTrace with complete span tree.

        Raises:
            AgentLoopTimeoutError: Loop exceeded max_iterations.
            AgentError: Unrecoverable error during execution.
        """
        trace_id = trace_id or generate_trace_id()
        trace_logger = inject_trace_id(logger, trace_id)
        trace = ExecutionTrace(trace_id=trace_id)

        # Init session
        self.memory.init_session(trace_id)
        self.memory.add_user_message(user_input)

        trace_logger.info(f"Agent loop started: '{user_input[:80]}...'")
        trace.add_event(EventType.ENTRY_START, message="agent_loop_started")

        try:
            for iteration in range(self._max_iterations):
                await self.hooks.fire_loop_start(iteration, self.memory.snapshot())

                # ── Step 1: LLM Call ──
                llm_span = trace.create_span(
                    name=f"llm_step_{iteration}",
                    span_type=SpanType.LLM_CALL,
                )
                llm_span.start()

                # ── Context window management: compact if over budget ──
                self.memory.working.compact()

                response = await self.llm.complete(
                    self.memory.working.get_context_for_llm(),
                    tools=self.router.get_available_tools_for_llm(),
                    trace_id=trace_id,
                )
                llm_span.finish(output=response.model_dump())

                self.memory.add_assistant_message(response.reasoning)

                # ── Step 2: Check termination ──
                if response.is_final:
                    trace_logger.info(f"Agent finished at iteration {iteration}")
                    trace.add_event(EventType.ENTRY_END, message=f"final_answer_reached_at_step_{iteration}")
                    break

                # ── Step 3: Tool Call ──
                if response.tool_call is None:
                    trace_logger.warning(f"No tool_call and not final at step {iteration}. Forcing termination.")
                    break

                tool_span = trace.create_span(
                    name=f"tool:{response.tool_call.tool_name}",
                    span_type=SpanType.TOOL_CALL,
                    parent_span_id=llm_span.span_id,
                    input_data=response.tool_call.input_data,
                )

                tool_name = response.tool_call.tool_name
                input_data = dict(response.tool_call.input_data)

                # ── PreToolUse hooks (input validation / rewriting / blocking) ──
                before = await self.hooks.fire_before_tool(tool_name, input_data)
                if before.decision == HookDecision.DENY:
                    tool_span.start()
                    tool_span.fail(before.reason)
                    trace_logger.warning(f"Tool blocked by PreToolUse hook: {before.reason}")
                    self.memory.working.append_observation(
                        {"error": before.reason, "tool": tool_name, "blocked": True}
                    )
                    continue
                if before.updated_input is not None:
                    input_data = before.updated_input
                response.tool_call.input_data = input_data

                tool_span.start()
                try:
                    tool_output = await self.router.route(response.tool_call)
                except Exception as e:
                    tool_span.fail(str(e))
                    await self.hooks.fire_on_error(e, tool_name, input_data)
                    trace_logger.error(f"Tool error at step {iteration}: {e}")
                    # Continue loop on tool error (degraded mode)
                    self.memory.working.append_observation({"error": str(e), "tool": tool_name})
                    continue

                # ── PostToolUse hooks (result verification / transform / context) ──
                after = await self.hooks.fire_after_tool(tool_name, input_data, tool_output)
                if after.decision == HookDecision.DENY:
                    tool_span.fail(f"PostToolUse rejected: {after.reason}")
                    trace_logger.warning(f"Tool result rejected: {after.reason}")
                    self.memory.working.append_observation(
                        {"error": after.reason, "tool": tool_name, "rejected": True}
                    )
                    continue
                if after.updated_output is not None:
                    tool_output = after.updated_output
                tool_span.finish(output=tool_output.model_dump())
                if after.additional_context:
                    self.memory.working.append_observation(
                        {"context": after.additional_context, "tool": tool_name}
                    )

                # ── Step 4: Observation → Memory ──
                self.memory.add_tool_result(tool_name, tool_output.model_dump())
                self.memory.working.append_observation(tool_output.model_dump())

                await self.hooks.fire_loop_end(iteration, self.memory.snapshot())

            else:
                # Exhausted max iterations
                raise AgentLoopTimeoutError(
                    message=f"Agent loop exceeded max iterations ({self._max_iterations})",
                    trace_id=trace_id,
                )

        except AgentLoopTimeoutError:
            raise
        except Exception as e:
            trace_logger.error(f"Agent loop crashed: {e}")
            raise AgentError(message=str(e), trace_id=trace_id) from e
        finally:
            trace.finalize()
            self.memory.end_session()
            self.llm.reset()
            trace_logger.info(f"Agent loop finished: status={trace.status.value}, duration={trace.total_duration_ms:.0f}ms")

        return trace