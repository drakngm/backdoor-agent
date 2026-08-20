"""
BaseTool: Abstract base class for all tools.

Every tool MUST:
  1. Declare a ToolContract as a class attribute
  2. Implement async execute(input) → output
  3. Use contract-defined input/output schemas

The validate_input() / validate_output() methods enforce contract compliance.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError

from app.tools.contract import ToolContract
from app.tools.schemas import ToolOutput
from app.core.logging import get_logger
from app.core.exceptions import ToolValidationError

logger = get_logger(__name__)


class BaseTool(ABC):
    """
    Abstract base class for all detection & utility tools.

    Subclass example:
        class MockSTRIPDetector(BaseTool):
            contract = ToolContract(...)
            async def execute(self, input_data): ...
    """

    # Subclasses MUST override this
    contract: ToolContract

    def validate_input(self, data: dict[str, Any]) -> bool:
        """
        Validate raw input dict against contract.input_schema.
        Raises ToolValidationError on failure.
        """
        try:
            self.contract.input_schema(**data)
            return True
        except ValidationError as e:
            raise ToolValidationError(
                message=f"Input validation failed for {self.contract.name}: {e}",
                details={"tool": self.contract.name, "errors": e.errors()},
            )

    def validate_output(self, output: BaseModel) -> bool:
        """
        Validate output object against contract.output_schema.
        Raises ToolValidationError on failure.
        """
        if not isinstance(output, self.contract.output_schema):
            raise ToolValidationError(
                message=f"Output type mismatch for {self.contract.name}: "
                        f"expected {self.contract.output_schema.__name__}, "
                        f"got {type(output).__name__}",
                details={"tool": self.contract.name},
            )
        return True

    @abstractmethod
    async def execute(self, input_data: BaseModel) -> BaseModel:
        """
        Execute the tool logic.

        Args:
            input_data: Must be an instance of contract.input_schema

        Returns:
            An instance of contract.output_schema
        """
        ...

    def get_contract_dict(self) -> dict[str, Any]:
        """Return contract as a dict (for LLM prompt generation)."""
        return {
            "name": self.contract.name,
            "description": self.contract.description,
            "timeout_ms": self.contract.timeout_ms,
            "requires_gpu": self.contract.requires_gpu,
            "retry_count": self.contract.retry_count,
            "tags": self.contract.tags,
        }