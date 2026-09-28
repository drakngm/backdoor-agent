"""
Report Generator: Aggregates tool outputs into a structured security report.

Consumes standardized ToolOutput (with confidence_score, risk_level, artifact)
and produces a human-readable + machine-readable report.
"""

from typing import Any
from datetime import datetime, timezone

from app.tools.schemas import RiskLevel, ToolOutput


def trace_evidence(trace: Any) -> dict[str, Any]:
    """Derive decision-chain / audit / data-flow evidence from a trace.

    Accepts a FourLevelTrace (or any object with `.replay()`) or an already-built
    replay dict. Returns fields with `evidence_incomplete` set when no trace is
    available, so the report degrades gracefully.
    """
    replay = None
    if trace is not None:
        replay = trace.replay() if hasattr(trace, "replay") else trace

    if replay is None:
        return {
            "decision_chain": None,
            "audit": None,
            "data_flow_summary": None,
            "evidence_incomplete": True,
        }

    return {
        "decision_chain": replay.get("decisions", []),
        "audit": {
            "verified": replay.get("audit_verified", False),
            "entries": replay.get("audit"),
        },
        "data_flow_summary": [
            {
                "step_id": d.get("step_id"),
                "tool_name": d.get("tool_name"),
                "input_hash": d.get("input_hash"),
                "output_hash": d.get("output_hash"),
            }
            for d in replay.get("data_flow", [])
        ],
        "evidence_incomplete": False,
    }


class ReportGenerator:
    """
    Aggregates multiple tool outputs into a unified detection report.

    Usage:
        gen = ReportGenerator()
        report = gen.generate(trace_id, tool_outputs, model_path="model.h5")
    """

    def generate(
        self,
        trace_id: str,
        tool_outputs: list[ToolOutput],
        model_path: str = "unknown",
        strategy: str = "unknown",
        trace: Any = None,
    ) -> dict[str, Any]:
        """
        Generate a structured security report.

        Args:
            trace_id: Trace ID for correlation.
            tool_outputs: List of ToolOutput from executed tools.
            model_path: Path to the scanned model.
            strategy: Strategy used for the scan.

        Returns:
            Structured report dict.
        """
        # Aggregate risk
        risk_levels = [out.risk_level for out in tool_outputs]
        if any(r == RiskLevel.HIGH for r in risk_levels):
            overall_risk = RiskLevel.HIGH
        elif any(r == RiskLevel.MEDIUM for r in risk_levels):
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        # Average confidence
        confidences = [out.confidence_score for out in tool_outputs if out.success]
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        # Count backdoor detections
        backdoor_detections = sum(
            1 for out in tool_outputs
            if out.success and out.data.get("is_backdoor", False)
        )

        verdict = "backdoor_detected" if backdoor_detections > 0 else "clean"

        tool_details = []
        for out in tool_outputs:
            tool_details.append({
                "tool": out.tool_name,
                "success": out.success,
                "duration_ms": out.duration_ms,
                "confidence": out.confidence_score,
                "risk_level": out.risk_level.value,
                "error": out.error,
                "artifact_refs": [a.name for a in out.artifact],
            })

        # Collect all artifacts
        all_artifacts = {}
        for out in tool_outputs:
            if out.artifact:
                all_artifacts[out.tool_name] = [a.model_dump() for a in out.artifact]

        report = {
            "report_id": f"report-{trace_id}",
            "trace_id": trace_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_path": model_path,
            "scan_strategy": strategy,
            "verdict": verdict,
            "overall_risk_level": overall_risk.value,
            "overall_confidence": avg_confidence,
            "tools_executed": len(tool_outputs),
            "backdoor_detections": backdoor_detections,
            "tool_details": tool_details,
            "artifacts": all_artifacts,
            "evidence": {
                "total_tools": len(tool_outputs),
                "successful_tools": sum(1 for o in tool_outputs if o.success),
                "failed_tools": sum(1 for o in tool_outputs if not o.success),
                "high_risk_tools": sum(1 for o in tool_outputs if o.risk_level == RiskLevel.HIGH),
            },
        }

        report.update(trace_evidence(trace))
        return report

    def format_text(self, report: dict[str, Any]) -> str:
        """Format report as human-readable text."""
        lines = [
            "=" * 60,
            f"  BACKDOOR DETECTION REPORT",
            "=" * 60,
            f"  Report ID:    {report['report_id']}",
            f"  Trace ID:     {report['trace_id']}",
            f"  Generated:    {report['generated_at']}",
            f"  Model:        {report['model_path']}",
            f"  Strategy:     {report['scan_strategy']}",
            "-" * 60,
            f"  VERDICT:      {report['verdict'].upper()}",
            f"  Risk Level:   {report['overall_risk_level']}",
            f"  Confidence:   {report['overall_confidence']}",
            "-" * 60,
            "  Tool Results:",
        ]
        for detail in report["tool_details"]:
            status = "✅" if detail["success"] else "❌"
            lines.append(
                f"    {status} {detail['tool']:30s} "
                f"risk={detail['risk_level']:6s} "
                f"conf={detail['confidence']:.2f} "
                f"({detail['duration_ms']:.0f}ms)"
            )
        lines.append("=" * 60)
        return "\n".join(lines)