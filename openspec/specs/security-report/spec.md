# security-report Specification

## Purpose
定义检测报告的内容契约：报告在聚合工具结论之外，必须包含可审计的决策链（CoT）与数据流/审计证据，使其可作为独立审计交付物。

## Requirements

### Requirement: Report includes decision chain

检测报告 SHALL 包含结构化决策链（CoT）字段，逐步呈现推理与决策依据。

#### Scenario: Report carries CoT steps

- **WHEN** 一次包含 Agent 决策的执行生成报告
- **THEN** 报告 SHALL 包含 `decision_chain`，其每步含 reasoning 与 decision 信息

### Requirement: Report includes audit evidence

检测报告 SHALL 包含审计证据：审计链的完整性校验状态与数据流摘要。

#### Scenario: Audit verification surfaced

- **WHEN** 报告基于一次已持久化的执行生成
- **THEN** 报告 SHALL 包含 `audit.verified` 校验结果与数据流摘要

#### Scenario: Missing trace degrades gracefully

- **WHEN** 生成报告时未提供四级 trace
- **THEN** 报告 SHALL 正常生成，并将相关字段置空并标注证据不完整
