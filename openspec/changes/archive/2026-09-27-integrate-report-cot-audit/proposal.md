# Proposal

## Why

PRD §7 将 Report 标为 80%，注明"未接 CoT/审计"。当前 `app/report/generator.py` 只聚合并发工具输出，报告不含决策链（CoT）与审计证据，无法独立支撑"事后审计"这一产品目标（PRD 1.2）。

## What Changes

- 报告新增结构化 CoT 决策链（observation/reasoning/decision/alternatives）。
- 报告新增审计级信息：审计链摘要与完整性校验状态、以及数据流摘要（工具输入→输出 hash 链）。
- 输出保持向后兼容：在现有报告 dict 上新增字段，不删除既有字段。
- 新增报告包含 CoT/审计字段的测试。

## Capabilities

### New Capabilities

- `security-report`: 检测报告的内容契约——聚合工具结论，并纳入决策链（CoT）与审计/数据流证据。

### Modified Capabilities

（无。）

## Impact

- 代码：`app/report/generator.py`（新增 CoT/审计入参或从 trace 读取）、调用方 `app/entry/dispatcher.py` / `app/api/hybrid.py`（传入四级 trace）。
- 输出：报告 dict 新增 `decision_chain`、`audit`、`data_flow_summary` 字段。
- 测试：`tests/` 新增报告测试。
- 与 PRD 关系：提升 Report 完成度，支撑 ET-4 审计与 1.2 可追溯目标。
