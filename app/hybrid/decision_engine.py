"""
DecisionEngine: the Agent Loop's high-level reasoning & decision layer.

Deterministic, rule-based (reproducible — HA-4). It maps
(model metadata, accumulated tool results) -> next Decision:

    convolutional model  -> STRIP first
    STRIP anomaly        -> Neural Cleanse (reverse trigger engineering)
    Neural Cleanse done  -> Activation Clustering (feature-space cross-check)
    all done             -> final report + verdict

Each Decision carries a `DetectionStep` (tool + params + depends_on) AND a
structured `CoTStep` (L3 decision trace: observation/reasoning/decision/
alternatives_considered), satisfying the forced system-prompt CoT format.
"""

from typing import Any, Optional

from app.hybrid.decisions import Decision, DetectionPlan, DetectionStep
from app.hybrid.model_analyzer import ModelMetadata
from app.trace.models import CoTStep, Alternative

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
            A Decision (next step with CoT, or final verdict with CoT).
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
        arch_kind = "卷积" if metadata.is_convolutional else "全连接"
        cot = CoTStep(
            step_id="strip_0",
            step="select_tool",
            observation=f"任务要求检测模型后门，模型为 {metadata.architecture}（{arch_kind}）架构",
            reasoning=f"{metadata.architecture} 是{arch_kind}架构，STRIP 是快速高效的初步筛查手段",
            decision="调用 STRIP 做扰动熵初步筛查",
            alternatives_considered=[
                Alternative(tool="neural_cleanse", reason_rejected="计算成本高，应先做快速筛查"),
                Alternative(tool="直接报告", reason_rejected="证据不足"),
            ],
            tool_name=STRIP,
        )
        return Decision(step=DetectionStep(
            step_id="strip_0",
            tool_name=STRIP,
            params={"model_path": metadata.path, "num_samples": 100},
            reasoning=cot.reasoning,
        ), cot=cot)

    def _decide_after_strip(
        self,
        metadata: ModelMetadata,
        strip: Optional[dict[str, Any]],
        strip_id: Optional[str],
    ) -> Decision:
        is_backdoor = bool(strip and strip.get("data", {}).get("is_backdoor"))

        if is_backdoor:
            cot = CoTStep(
                step_id="neural_cleanse_0",
                step="select_tool",
                observation="STRIP 检测发现扰动熵异常降低，表明模型对输入扰动不敏感，符合后门特征",
                reasoning=(
                    "扰动熵降低可能由后门/模型过拟合/数据问题导致，需进一步缩小原因范围。"
                    "Neural Cleanse 可逆向重建潜在触发器，若重建成功则强指示后门存在。"
                ),
                decision="调用 Neural Cleanse 进行触发器逆向重建",
                alternatives_considered=[
                    Alternative(tool="activation_clustering",
                                reason_rejected="需要大量干净/中毒样本标注，当前场景缺乏标注数据"),
                    Alternative(tool="直接报告", reason_rejected="单一检测器结果不可靠"),
                ],
                tool_name=NEURAL_CLEANSE,
            )
            return Decision(step=DetectionStep(
                step_id="neural_cleanse_0",
                tool_name=NEURAL_CLEANSE,
                params={"model_path": metadata.path, "num_classes": metadata.num_classes},
                depends_on=[strip_id] if strip_id else [],
                reasoning=cot.reasoning,
            ), cot=cot)

        confidence = round(strip.get("confidence_score", 0.0), 2) if strip else 0.0
        cot = CoTStep(
            step_id="finalize",
            step="finalize",
            observation="STRIP 未发现扰动熵异常",
            reasoning="扰动熵在正常范围内，无后门特征信号",
            decision="生成报告：模型判定为干净",
            confidence=confidence,
        )
        return Decision(
            is_final=True,
            verdict="clean",
            confidence=confidence,
            final_answer="STRIP 未发现扰动熵异常，模型判定为干净",
            cot=cot,
        )

    def _decide_after_nc(self, metadata: ModelMetadata, nc_id: Optional[str]) -> Decision:
        cot = CoTStep(
            step_id="activation_clustering_0",
            step="select_tool",
            observation="Neural Cleanse 检测到疑似后门（异常指数异常）",
            reasoning=(
                "需交叉验证：Activation Clustering 可检查干净/中毒样本在特征空间是否分离，"
                "以区分后门类型（clean-label / subtle trigger）"
            ),
            decision="调用 Activation Clustering 做特征空间交叉验证",
            alternatives_considered=[
                Alternative(tool="直接报告", reason_rejected="缺乏特征空间证据，不足以确认后门类型"),
            ],
            tool_name=ACTIVATION_CLUSTERING,
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
            reasoning=cot.reasoning,
        ), cot=cot)

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

            cot = CoTStep(
                step_id="finalize",
                step="finalize",
                observation=f"三个检测器已完成，{len(detections)} 个报告后门特征",
                reasoning=note,
                decision="生成检测报告：模型疑似存在后门",
                confidence=confidence,
            )
            return Decision(
                is_final=True,
                verdict="backdoor_suspected",
                confidence=confidence,
                final_answer=(
                    f"模型疑似存在后门，置信度 {int(confidence * 100)}%，"
                    f"建议进行更深入的触发器逆向分析。（{note}）"
                ),
                cot=cot,
            )

        confidence = round(
            max((r.get("confidence_score", 0.0) for r in results.values()), default=0.0), 2
        )
        cot = CoTStep(
            step_id="finalize",
            step="finalize",
            observation="多检测器均未发现后门特征",
            reasoning="无一致的后门信号",
            decision="生成检测报告：模型判定为干净",
            confidence=confidence,
        )
        return Decision(
            is_final=True,
            verdict="clean",
            confidence=confidence,
            final_answer="多检测器均未发现后门特征，模型判定为干净",
            cot=cot,
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
