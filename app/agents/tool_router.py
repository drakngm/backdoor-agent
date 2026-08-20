"""
ToolRouter: Receives LLM output, matches to a registered tool, and executes it.

In production, the LLM returns a structured tool_call JSON.
In MVP, we use a mock LLM that returns hardcoded tool call sequences.

The router:
  1. Validates the tool exists in ToolRegistry
  2. Validates input against the tool's contract
  3. Executes the tool with timeout enforcement
  4. Returns the tool's output
"""

import asyncio
from typing import Any, Optional

from app.llm.base import ToolCallRequest
from app.tools.registry import ToolRegistry, get_tool_registry
from app.tools.schemas import ToolOutput
from app.core.logging import get_logger
from app.core.exceptions import ToolNotFoundError, ToolExecutionError, ToolTimeoutError

logger = get_logger(__name__)


class ToolRouter:
    """
    Routes tool calls from the LLM to the correct tool implementation.

    Responsibilities:
      - Tool discovery (via ToolRegistry)
      - Input validation (via ToolContract.input_schema)
      - Execution with timeout (via contract.timeout_ms)
      - Output validation (via ToolContract.output_schema)
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_tool_registry()

    async def route(self, request: ToolCallRequest) -> ToolOutput:
        """
        Route a single tool call.

        Args:
            request: ToolCallRequest with tool_name and input_data.

        Returns:
            ToolOutput from the executed tool.

        Raises:
            ToolNotFoundError: Tool not registered.
            ToolTimeoutError: Execution exceeded contract timeout.
            ToolExecutionError: Execution failed unexpectedly.
        """
        tool = self.registry.get(request.tool_name)

        # Validate input
        tool.validate_input(request.input_data)

        # Build typed input
        try:
            typed_input = tool.contract.input_schema(**request.input_data)
        except Exception as e:
            raise ToolExecutionError(
                message=f"Failed to construct input for {request.tool_name}: {e}",
                details={"tool": request.tool_name, "input": request.input_data},
            )

        # Execute with timeout
        timeout_seconds = tool.contract.timeout_ms / 1000.0
        try:
            result = await asyncio.wait_for(
                tool.execute(typed_input),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise ToolTimeoutError(
                message=f"Tool {request.tool_name} timed out after {timeout_seconds}s",
                details={"tool": request.tool_name, "timeout_ms": tool.contract.timeout_ms},
            )
        except Exception as e:
            raise ToolExecutionError(
                message=f"Tool {request.tool_name} execution failed: {e}",
                details={"tool": request.tool_name, "error": str(e)},
            )

        # Validate output
        tool.validate_output(result)

        logger.info(
            f"Tool routed: {request.tool_name} → success={result.success}",
            extra={"trace_id": result.trace_id},
        )
        return result

    async def route_many(self, requests: list[ToolCallRequest]) -> list[ToolOutput]:
        """
        Route multiple tool calls concurrently.

        Args:
            requests: List of ToolCallRequest items.

        Returns:
            List of ToolOutput items (order preserved).
        """
        tasks = [self.route(req) for req in requests]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    def get_available_tools_for_llm(self) -> list[dict[str, Any]]:
        """Generate LLM-friendly tool descriptions."""
        tools_list = []
        for tool in self.registry.list_all():
            tools_list.append({
                "name": tool.contract.name,
                "description": tool.contract.description,
                "timeout_ms": tool.contract.timeout_ms,
                "requires_gpu": tool.contract.requires_gpu,
                "tags": tool.contract.tags,
            })
        return tools_list