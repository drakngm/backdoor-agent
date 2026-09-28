# Design

## Context

See proposal.md - Why. 四级 trace（含结构化 CoT 与 hash 链审计）已在 `app/trace/` 落地，`FourLevelTrace.replay()` 可提供决策链与审计。报告生成器 `ReportGenerator.generate(trace_id, tool_outputs, ...)` 已接收 `trace_id`，可在同一执行上下文中拿到 trace 对象。

## Goals / Non-Goals

**Goals:**

- 报告可作为独立审计交付物：包含结论 + 决策依据 + 审计证据。
- 向后兼容既有报告消费方。

**Non-Goals:**

- 不改变工具输出 schema，不改动四级 trace 模型。
- 不做报告的可视化渲染（Mermaid 由 trace 提供）。

## Decisions

- **D1：由调用方传入 `FourLevelTrace`，生成器只做聚合。** 保持 `ReportGenerator` 无外部状态、可单测。理由：职责清晰。替代方案（生成器自行按 trace_id 读取存储）会引入对存储层的耦合。
- **D2：新增字段而非重构。** 报告新增 `decision_chain`（CoT 步骤列表）、`audit`（`{verified, entries, chain_head}`）、`data_flow_summary`（边列表）。理由：兼容。
- **D3：审计校验状态显式输出。** 报告携带 `audit.verified`，篡改可被下游发现。

## Risks / Trade-offs

- [trace 缺失时报告不完整] → 参数可选：无 trace 时字段为 `null` 并标注 `evidence_incomplete=true`，不阻断报告生成。
- [报告体积增大] → CoT/审计摘要化（截断超长字段），保留关键结构。
