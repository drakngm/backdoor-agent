# Design

## Context

See proposal.md - Why. 核心 FastAPI 暴露 4 个端点（`/health`、`/run_agent`、`/run_workflow`、`/run_hybrid`）——目前**没有**仪表盘读模型（overview/metrics/timeline/detectors/memory/traces/logs/dag）。BFF 的 `mock_data.py` 已定义这些形状；`execute.py` 已示范 httpx 调用与降级。

## Goals / Non-Goals

**Goals:**

- 界面上每个数据块都能反映其来源，核心在线时展示真实数据。
- 降级行为可配置、可测试、可观测。

**Non-Goals:**

- 不在本期为核心平台新增仪表盘聚合端点（若缺数据，BFF 以现有核心端点 + 前端派生实现，缺口记录为开放问题）。
- 不改动前端视觉设计。
- 不做 Web 侧鉴权（并入 access-control）。

## Decisions

- **D1：BFF 统一 `core_client` 封装。** 集中超时、异常与降级逻辑，各路由复用。理由：避免每路由重复 try/except。
- **D2：优先 core、失败回退 mock，并在响应加 `source`。** 理由：保留"无后端也能演示"的产品价值，同时消除数据来源歧义。
- **D3：核心缺失的读模型由 BFF 聚合/派生。** 对核心没有的端点（如 metrics），BFF 基于 `/health` 与已持久化 trace 计算，无法计算时降级 mock。理由：不改核心即可联通；把"核心是否应提供聚合端点"列为开放问题。

## Risks / Trade-offs

- [核心端点不足，部分面板仍只能 mock] → 明确标注来源并在文档记录缺口，二期再决定是否下沉到核心。
- [双后端联调复杂度上升] → 提供一键启动脚本与集成测试固定契约。
- [网络抖动导致误降级] → 可配置超时与重试，响应标注来源便于排查。
