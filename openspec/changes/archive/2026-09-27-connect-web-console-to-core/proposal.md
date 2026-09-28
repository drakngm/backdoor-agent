# Proposal

## Why

`web/`（commit `037f7a2`，未进 PRD）定位为可视化指挥中心，但 BFF 中仅 `routers/execute.py` 会通过 httpx 调用核心 API，`dashboard` / `detection` / `telemetry` / `workflow` 路由全部直接返回 `mock_data`，前端 `src/api/client.ts` 还有本地 mock 降级；用户无法判断界面数据是真实还是仿真，Web 与核心平台实际上处于脱节状态。

## What Changes

- BFF 各读模型改为**优先调用核心 API**，核心不可用（且允许时）再回退 `mock_data`。
- 响应用显式标注数据来源（`source: core | mock`），前端据此展示"真实/仿真"标识。
- 统一核心 API 调用封装（超时、错误处理、降级策略可配置）。
- 新增 BFF 集成测试：核心可用时返回 core 数据、不可用时回退 mock。

## Capabilities

### New Capabilities

- `web-console`: Web 指挥中心（BFF + 前端）的行为契约——数据来源、降级策略与来源可见性。

### Modified Capabilities

（无。）

## Impact

- 代码：`web/backend/app/routers/*`、`web/backend/app/config.py`、`web/backend/app/mock_data.py`（降级用）、`web/frontend/src/api/client.ts` 与相关页面。
- 配置：`CORE_API_URL`、`ALLOW_MOCK_FALLBACK` 语义明确化。
- 测试：`web/backend` 新增集成测试。
- 文档：`web/README.md`、根 `README.md` 增补 Web 模块说明（当前 PRD 未涵盖）。
