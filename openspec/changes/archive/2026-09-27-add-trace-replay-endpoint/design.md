# Design

## Context

See proposal.md - Why. `FourLevelTrace` 已聚合系统/数据/决策/审计四级并支持 `replay()` 与 `compare()`（内容寻址，见 `app/trace/trace.py`）。缺的是持久化与对外端点。`Dispatcher`（`app/entry/dispatcher.py`）是三种模式的统一入口，适合挂接持久化。数据目录约定见 `configs/settings.py` 的 `BACKDOOR_DATA_DIR`。

## Goals / Non-Goals

**Goals:**

- 任一执行结束后，其四级 trace 可被同一 `trace_id` 在后续请求中完整取回。
- 提供稳定、可测试的 `/replay/{trace_id}` 响应契约。

**Non-Goals:**

- 不做分布式/数据库存储或远程查询服务。
- 不做 trace 的鉴权与多租户隔离（见 productionize-embedding-and-access）。
- 不改变现有四级 trace 的数据模型语义。

## Decisions

- **D1：落盘 JSON，按内容寻址。** 存储路径 `<DATA_DIR>/traces/<trace_id>.json`，写入原子化（临时文件 + 重命名）。理由：MVP 满足"可事后审计"，与 NFR-5（不落敏感信息）和 Windows 路径兼容一致。替代方案（SQLite/Redis）留待后续。
- **D2：在 `Dispatcher` 统一持久化。** 三种模式复用同一落盘点，避免各处重复。理由：单一入口，最小侵入。
- **D3：端点返回聚合视图。** `GET /replay/{trace_id}` 返回 `{trace_id, timeline, decisions(CoT), data_flow, audit, mermaid}`；`audit` 附 `verify()` 校验结果。
- **D4：未命中返回 404。** 找不到 `trace_id` 时返回 404 与结构化错误，而非 500。

## Risks / Trade-offs

- [落盘体积增长] → 以 trace_id 命名、单文件写入；预留清理/归档策略（本期不实现）。
- [敏感信息落盘] → 严格遵守 NFR-5，持久化前过滤凭据字段。
- [并发写同一 id] → 内容寻址 + 原子重命名降低竞态风险。
