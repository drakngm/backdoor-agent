# Proposal

## Why

PRD 4.5（ET-5）要求"根据 trace_id 重建完整执行流程"，README Production Path #5 也列出 `/replay/{trace_id}`。当前回放仅以方法形式存在（`app/trace/trace.py` 的 `FourLevelTrace.replay()`），API 只有 4 个端点（`/health`、`/run_agent`、`/run_workflow`、`/run_hybrid`），且 trace 执行后不落盘，无法按 id 事后回放或审计。

## What Changes

- 新增四级 Trace 的持久化存储（落盘 JSON，内容寻址），使 trace 可跨请求按 `trace_id` 取回。
- 新增 `GET /replay/{trace_id}` 端点，返回完整审计链：时间线 + 决策链（CoT）+ 数据流 + 审计链。
- 在 agent / workflow / hybrid 执行结束时持久化 trace。
- 新增回放端点与持久化往返的测试。

## Capabilities

### New Capabilities

- `trace-observability`: 四级 Trace 的持久化、按 trace_id 回放、以及跨执行对比的对外行为。

### Modified Capabilities

（无。）

## Impact

- 代码：`app/trace/`（新增持久化存储层）、`app/api/`（新增 replay 路由并在 `router.py` 聚合）、`app/entry/dispatcher.py`（执行后持久化）、可选 `app/core/execution_trace.py` 集成。
- API：新增 `GET /replay/{trace_id}`；`/health` 不变。
- 存储：本地 JSON 落盘，沿用 `BACKDOOR_DATA_DIR`。
- 与 PRD 关系：关闭 ET-5 与 Production Path #5。
