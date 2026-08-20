"""
ToolAdapter: convenience base for wrapping a standalone algorithm into a Tool.

Separates the algorithm (the `run` method) from the tool plumbing (contract
validation, timing, error normalization). Algorithm authors only implement
`run()` and declare a `manifest`; the adapter supplies `execute()`.

This is the "Adapter 模式" of the Unified Tool Contract:

    external/third-party algorithm -> ToolAdapter -> BaseTool (registry-ready)

Subclasses:
  - declare a `manifest` (ToolContract / ToolManifest)
  - implement `async def run(self, input_data) -> output`
"""

import time
from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from app.tools.base import BaseTool
from app.tools.contract import ToolContract
from app.tools.schemas import ToolOutput
from app.core.logging import get_logger
from app.core.exceptions import ToolExecutionError

logger = get_logger(__name__)


class ToolAdapter(BaseTool):
    """
    Adapts a standalone algorithm into a registry-ready tool.

    Usage:
        class STRIPTool(ToolAdapter):
            manifest = ToolContract(
                name="strip_detect",
                description="...",
                input_schema=STRIPInput,
                output_schema=STRIPOutput,
                timeout_ms=60000,
                tags=["detection"],
            )

            async def run(self, input_data: STRIPInput) -> STRIPOutput:
                result = strip_detect(...)
                return STRIPOutput(...)
    """

    # Subclasses declare their contract as `manifest` (see ToolManifest alias).
    manifest: ToolContract

    @property
    def contract(self) -> ToolContract:
        """Expose `manifest` as the BaseTool `contract` used by the registry."""
        return self.manifest

    async def execute(self, input_data: BaseModel) -> BaseModel:
        """
        Wrap the algorithm's `run()` with timing + error normalization.

        Input/output validation against the contract is performed by the
        ToolRouter before/after calling this method.
        """
        start = time.perf_counter()
        try:
            output = await self.run(input_data)
        except Exception as e:
            logger.error(f"Tool '{self.contract.name}' execution failed: {e}")
            raise ToolExecutionError(
                message=f"Tool {self.contract.name} execution failed: {e}",
                details={"tool": self.contract.name, "error": str(e)},
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        if isinstance(output, ToolOutput):
            output.duration_ms = round(elapsed_ms, 3)
        return output

    @abstractmethod
    async def run(self, input_data: BaseModel) -> BaseModel:
        """Algorithm core. Must return an instance of `manifest.output_schema`."""
        ...
