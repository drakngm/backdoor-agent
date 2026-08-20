"""
DecisionEngine: the Agent Loop's high-level reasoning & decision layer.

Deterministic, rule-based (reproducible — HA-4). It maps
(model metadata, accumulated tool results) -> next Decision:

    convolutional model  -> STRIP first
    STRIP anomaly        -> Neural Cleanse (reverse trigger engineering)
    Neural Cleanse done  -> Activation Clustering (feature-space cross-check)
    all done             -> final report + verdict

Each Decision carries a `DetectionStep` (tool + params + depends_on) so the
compiler can turn it into a DAG node. The `reasoning` strings are the CoT-style
rationale; a production variant could generate these via the LLMClient while
keeping the *decision* (tool choice) deterministic.
"""

from typing import Any, Optional

from app.hybrid.decisions import Decision, DetectionPlan, DetectionStep
from app.hybrid.model_analyzer import ModelMetadata

# Tool name constants (mirror ToolRegistry names)
STRIP = "strip_detect"
NEURAL_CLEANSE = "neural_cleanse"
ACTIVATION_CLUSTERING = "activation_clustering"


class DecisionEngine:
    """Rule-based detection decision engine (deterministic)."""

    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps

    def decide(
        self,
        metadata: ModelMetadata,
        results: dict[str, dict[str, Any]],
        plan: DetectionPlan,
    ) -> Decision:
        """
        Decide the next action given model metadata and accumulated results.

        Args:
            metadata: Analyzed model metadata.
            results: dict of step_id -> tool output dict (ToolOutput.model_dump()).
            plan: The DetectionPlan accumulated so far (for step dependency ids).

        Returns:
            A Decision (next step, or final verdict).
        """
        tool_names = {r.get("tool_name") for r in results.values()}

        if STRIP not in tool_names:
            return self._decide_strip(metadata)

        strip_id = self._find_step_id(plan, STRIP)
        strip = self._result_for(STRIP, results)

        if NEURAL_CLEANSE not in tool_names:
            return self._decide_after_strip(metadata, strip, strip_id)

        nc_id = self._find_step_id(plan, NEURAL_CLEANSE)

        if ACTIVATION_CLUSTERING not in tool_names:
            return self._decide_after_nc(metadata, nc_id)

        return self._finalize(results)

    # ── Decision builders ────────────────────────────────────────────

    def _decide_strip(self, metadata: ModelMetadata) -> Decision:
        reasoning = (
            f"{metadata.architecture} 是{'卷积' if metadata.is_convolutional else '全连接'}架构，"
            "先跑 STRIP 做初步筛查"
        )
        return Decision(step=DetectionStep(
            step_id="strip_0",
            tool_name=STRIP,
            params={"model_path": metadata.path, "num_samples": 100},
            reasoning=reasoning,
        ))

    def _decide_after_strip(
        self,
        metadata: ModelMetadata,
        strip: Optional[dict[str, Any]],
        strip_id: Optional[str],
    ) -> Decision:
        is_backdoor = bool(strip and strip.get("data", {}).get("is_backdoor"))

        if is_backdoor:
            reasoning = (
                "扰动熵异常降低，但无法确认具体后门类型 → "
                "调度 Neural Cleanse 做逆向触发器重建"
            )
            return Decision(step=DetectionStep(
                step_id="neural_cleanse_0",
                tool_name=NEURAL_CLEANSE,
                params={
                    "model_path": metadata.path,
                    "num_classes": metadata.num_classes,
                },
                depends_on=[strip_id] if strip_id else [],
                reasoning=reasoning,
            ))

        confidence = round(strip.get("confidence_score", 0.0), 2) if strip else 0.0
        return Decision(
            is_final=True,
            verdict="clean",
            confidence=confidence,
            final_answer="STRIP 未发现扰动熵异常，模型判定为干净",
        )

    def _decide_after_nc(self, metadata: ModelMetadata, nc_id: Optional[str]) -> Decision:
        reasoning = (
            "Neural Cleanse 检测到疑似后门 → "
            "运行 Activation Clustering 做特征空间交叉验证"
        )
        return Decision(step=DetectionStep(
            step_id="activation_clustering_0",
            tool_name=ACTIVATION_CLUSTERING,
            params={
                "model_path": metadata.path,
                "layer_name": metadata.layer_hint,
                "n_clusters": 3,
            },
            depends_on=[nc_id] if nc_id else [],
            reasoning=reasoning,
        ))

    def _finalize(self, results: dict[str, dict[str, Any]]) -> Decision:
        detections = [
            r for r in results.values() if r.get("data", {}).get("is_backdoor")
        ]

        if detections:
            confidence = round(max(r.get("confidence_score", 0.0) for r in detections), 2)
            ac = self._result_for(ACTIVATION_CLUSTERING, results)
            ac_anomalous = (ac or {}).get("data", {}).get("n_anomalous_clusters", 0)
            if ac is not None and not ac_anomalous:
                note = ("Activation Clustering 显示干净样本和中毒样本在特征空间无显著分离 → "
                        "可能是 clean-label attack 或触发器非常 subtle")
            else:
                note = "多检测器一致指向后门存在"
            return Decision(
                is_final=True,
                verdict="backdoor_suspected",
                confidence=confidence,
                final_answer=(
                    f"模型疑似存在后门，置信度 {int(confidence * 100)}%，"
                    f"建议进行更深入的触发器逆向分析。（{note}）"
                ),
            )

        confidence = round(
            max((r.get("confidence_score", 0.0) for r in results.values()), default=0.0), 2
        )
        return Decision(
            is_final=True,
            verdict="clean",
            confidence=confidence,
            final_answer="多检测器均未发现后门特征，模型判定为干净",
        )

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _result_for(tool_name: str, results: dict[str, dict[str, Any]]) -> Optional[dict[str, Any]]:
        for r in results.values():
            if r.get("tool_name") == tool_name:
                return r
        return None

    @staticmethod
    def _find_step_id(plan: DetectionPlan, tool_name: str) -> Optional[str]:
        for step in plan.steps:
            if step.tool_name == tool_name:
                return step.step_id
        return None
