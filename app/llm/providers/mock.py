"""
Mock LLM client — scripted, in-process provider.

Returns a pre-scripted sequence of tool calls to exercise the Agent Loop without
any API key. This mirrors the previous MockLLM but conforms to the LLMClient
interface.
"""

from typing import Any, Optional

from app.llm.base import LLMClient, LLMProvider, LLMResponse, ToolCallRequest


class MockLLMClient(LLMClient):
    """Scripted LLM that returns a fixed detection workflow."""

    provider = LLMProvider.MOCK

    # Pre-scripted detection workflow
    DETECTION_FLOW = [
        LLMResponse(
            reasoning="User wants to detect backdoors. First, I need to run STRIP detection.",
            tool_call=ToolCallRequest(tool_name="strip_detect", input_data={
                "trace_id": "PLACEHOLDER",
                "model_path": "model.h5",
                "num_samples": 100,
            }),
        ),
        LLMResponse(
            reasoning="STRIP detection complete. Now I should run Neural Cleanse for cross-validation.",
            tool_call=ToolCallRequest(tool_name="neural_cleanse", input_data={
                "trace_id": "PLACEHOLDER",
                "model_path": "model.h5",
                "num_classes": 10,
            }),
        ),
        LLMResponse(
            reasoning="Neural Cleanse done. Running Activation Clustering as a third detector.",
            tool_call=ToolCallRequest(tool_name="activation_clustering", input_data={
                "trace_id": "PLACEHOLDER",
                "model_path": "model.h5",
                "layer_name": "dense_2",
                "n_clusters": 3,
            }),
        ),
        LLMResponse(
            is_final=True,
            reasoning="All three detectors have completed. Aggregating results...",
            final_answer=(
                "Backdoor detection complete. Results:\n"
                "- STRIP: entropy_score analyzed, verdict included\n"
                "- Neural Cleanse: anomaly_index computed, verdict included\n"
                "- Activation Clustering: clusters analyzed, verdict included\n"
                "Final verdict is available in the execution trace."
            ),
        ),
    ]

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None,
                 base_url: Optional[str] = None, **kwargs: Any):
        self._step = 0

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        trace_id: str = "",
    ) -> LLMResponse:
        """Return the next pre-scripted response."""
        if self._step >= len(self.DETECTION_FLOW):
            return LLMResponse(
                is_final=True,
                reasoning="Maximum steps reached. Stopping.",
                final_answer="Agent stopped: max iterations reached.",
            )

        response = self.DETECTION_FLOW[self._step]

        # Inject trace_id into tool call input
        if response.tool_call:
            response.tool_call.input_data["trace_id"] = trace_id

        self._step += 1
        return response

    def reset(self) -> None:
        self._step = 0


# Backward-compatible alias for code/tests importing MockLLM from agent_loop.
MockLLM = MockLLMClient
