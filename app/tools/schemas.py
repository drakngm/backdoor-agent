"""
Unified Tool Input/Output schemas.

All Tool inputs MUST inherit from ToolInput.
All Tool outputs MUST inherit from ToolOutput.

Standardized safety fields (confidence_score, risk_level, artifact)
make cross-tool aggregation possible in the Report Generator.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Standardized risk level for security tool outputs."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ToolInput(BaseModel):
    """Base class for all tool inputs.

    All tool-specific input schemas MUST inherit from this.
    """
    trace_id: str = Field(..., description="Trace ID for end-to-end correlation")
    params: dict[str, Any] = Field(default_factory=dict, description="Tool-specific parameters")


class Artifact(BaseModel):
    """
    Standardized artifact produced by a tool.

    Replaces the previous loose `dict` artifact so that files and intermediate
    results are uniformly modeled (name, kind, path, hash, size, format). This
    enables cross-tool dataflow tracing, integrity checking, and audit.

    Example:
        Artifact(
            name="entropy_distribution",
            type="distribution",
            path="/tmp/strip_entropy_trc-123.npy",
            hash="sha256:...",
            size_bytes=2048,
            format="npy",
            metadata={"threshold_used": 0.5},
        )
    """

    name: str = Field(..., description="Unique artifact identifier within a tool output")
    type: str = Field(..., description="Artifact kind (distribution, matrix, image, scalar, stats, ...)")
    path: Optional[str] = Field(default=None, description="Filesystem/object-store location")
    hash: Optional[str] = Field(default=None, description="sha256 content hash for integrity")
    size_bytes: Optional[int] = Field(default=None, description="Size in bytes if applicable")
    format: Optional[str] = Field(default=None, description="File/data format (npy, png, json, ...)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra structured metadata")


class ToolOutput(BaseModel):
    """
    Base class for all tool outputs.

    All tool-specific output schemas MUST inherit from this.

    Standardized fields:
      - confidence_score: 0.0 ~ 1.0  — how confident the tool is in its result
      - risk_level:        LOW/MEDIUM/HIGH — normalized risk classification
      - artifact:          list[Artifact] — standardized intermediate artifacts
    """

    trace_id: str
    tool_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict, description="Tool-specific result payload")
    error: Optional[str] = None
    duration_ms: float = 0.0

    # ── Standardized safety fields ──────────────────────────────────────
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence of the tool in its result (0.0 ~ 1.0)",
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Normalized risk level classification",
    )
    artifact: list[Artifact] = Field(
        default_factory=list,
        description="Standardized intermediate artifacts (activation maps, trigger candidates, logs, etc.)",
    )