"""
ToolContract: Metadata / interface contract for every Tool.

Decouples tool metadata (name, schema, timeout, GPU requirement, tags)
from the runtime execution logic. Used by:
- ToolRegistry: registration, discovery, LLM prompt generation
- Agent Loop / Workflow Executor: pre-flight validation
- Scheduler: GPU resource allocation
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolContract(BaseModel):
    """
    Each tool declares its own contract as a class attribute.

    Example:
        class MockSTRIPDetector(BaseTool):
            contract = ToolContract(
                name="strip_detect",
                description="STRIP detection: perturb input samples and observe entropy change",
                input_schema=STRIPInput,
                output_schema=STRIPOutput,
                timeout_ms=60000,
                requires_gpu=True,
                retry_count=2,
                tags=["detection", "gpu"],
            )
    """

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Natural language description for LLM consumption")
    version: str = "1.0.0"

    # Pydantic model classes (validated on tool execution)
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    timeout_ms: int = 30000
    requires_gpu: bool = False
    retry_count: int = 0

    tags: list[str] = Field(default_factory=list, description="Classification tags: detection, loader, report, gpu, ...")

    model_config = {"arbitrary_types_allowed": True}


# ToolManifest is the product-facing name for a tool's declarative contract.
# Kept as an alias so existing ToolContract usages remain valid while adopting
# the "Unified Tool Contract" terminology used in the PRD.
ToolManifest = ToolContract