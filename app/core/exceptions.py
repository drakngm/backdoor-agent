"""
Custom exception hierarchy for the Backdoor Agent system.

All application-level exceptions inherit from AgentSystemError
so they can be caught uniformly at the API layer.
"""


class AgentSystemError(Exception):
    """Base exception for all agent system errors."""

    def __init__(self, message: str, trace_id: str = "", details: dict = None):
        super().__init__(message)
        self.message = message
        self.trace_id = trace_id
        self.details = details or {}


class AgentError(AgentSystemError):
    """Errors originating in the Agent Runtime layer (agent_loop, tool_router)."""


class AgentLoopTimeoutError(AgentError):
    """Agent loop exceeded max iterations or timeout."""


class AgentLLMError(AgentError):
    """LLM API call failed or returned malformed response."""


class ToolError(AgentSystemError):
    """Errors originating in the Tool layer."""


class ToolNotFoundError(ToolError):
    """Requested tool not found in ToolRegistry."""


class ToolExecutionError(ToolError):
    """Tool execution failed at runtime."""


class ToolTimeoutError(ToolError):
    """Tool execution exceeded its contract timeout."""


class ToolValidationError(ToolError):
    """Tool input failed schema validation against its contract."""


class WorkflowError(AgentSystemError):
    """Errors originating in the Workflow layer."""


class WorkflowStrategyError(WorkflowError):
    """Unknown or invalid scan strategy."""


class TaskGraphError(WorkflowError):
    """Invalid TaskGraph (cycle detected, missing dependency, etc.)."""


class WorkflowExecutionError(WorkflowError):
    """Workflow execution failed mid-flight."""


class ConfigurationError(AgentSystemError):
    """Configuration errors (missing env vars, invalid values, etc.)."""


class MemoryError(AgentSystemError):
    """Errors in the Memory subsystem."""


class TraceError(AgentSystemError):
    """Errors in the Execution Trace subsystem."""