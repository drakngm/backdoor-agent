# Spec Delta

## Purpose

定义平台对执行 Trace 的持久化与回放能力：执行结束后可持久保存四级 trace，并可按 trace_id 取回完整审计链用于事后审计与流程重现。

## ADDED Requirements

### Requirement: Trace persistence after execution

系统 SHALL 在每次 agent / workflow / hybrid 执行结束后持久化其四级 trace，并以 `trace_id` 作为可检索键，持久化内容 SHALL 排除凭据等敏感信息。

#### Scenario: Trace is persisted on completion

- **WHEN** 一次 hybrid 执行结束并返回 `trace_id`
- **THEN** 系统 SHALL 将该 trace 持久化到本地存储，且可通过该 `trace_id` 再次读取

#### Scenario: No credentials persisted

- **WHEN** 执行上下文中包含 API key 等敏感字段
- **THEN** 持久化内容 SHALL 不包含这些敏感字段

### Requirement: Replay by trace id

系统 SHALL 提供 `GET /replay/{trace_id}` 端点，返回该次执行的完整审计链，包含时间线、决策链（CoT）、数据流与审计链；审计链 SHALL 附带完整性校验结果。

#### Scenario: Successful replay

- **WHEN** 请求一个已持久化的 `trace_id`
- **THEN** 响应 SHALL 包含 `trace_id`、`timeline`、`decisions`、`data_flow`、`audit`，且 `audit` 含校验状态

#### Scenario: Replay of unknown trace id

- **WHEN** 请求一个不存在的 `trace_id`
- **THEN** 系统 SHALL 返回 404 与结构化错误信息，而非 500
