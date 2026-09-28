# Proposal

## Why

PRD 的里程碑状态与实际代码脱节：§8 仍将 M3 标为"🔄 下一步"、M4 未标 ✅，但 `app/hybrid/`、`app/memory/hierarchical.py` 与提交记录显示二者已完成；README/Docker 描述与实际存在偏差。同时，虽然现有 132 个测试通过，但新能力（真实 NC/AC、`/replay`、报告 CoT/审计、BFF 集成）缺少用例。本变更只做文档与测试对齐，不改变系统行为。

## What Changes

- 对账 PRD §7 完成度表与 §8 里程碑状态，修正滞后标记、占位与 Gap 描述。
- 修正 `README.md` / `readme_Zh.md` 与实现不一致处；明确 Docker 为"接口保留，本期不实现"（Out of Scope）。
- 补充测试缺口（随相关变更落地）：真实 NC/AC、`/replay`、报告 CoT/审计、BFF 集成。
- 保持 `pytest tests/ -v` 全绿。

## Capabilities

### New Capabilities

（无。本变更为纯文档与测试对齐，不改变 spec 级行为。）

### Modified Capabilities

（无。同上。）

> 说明：本变更不产生 spec delta，已在 `.openspec.yaml` 设置 `skip_specs: true`。

## Impact

- 文档：`PRD.md`、`README.md`、`readme_Zh.md`。
- 测试：`tests/`（新增/补强用例）。
- 不改变对外 API 与行为；无生产代码语义变化。
