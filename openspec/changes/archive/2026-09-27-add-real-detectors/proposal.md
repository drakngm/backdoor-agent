# Proposal

## Why

PRD 4.3（UTC-6）验收要求 STRIP / Neural Cleanse / Activation Clustering 三者均有真实（或可运行）实现并通过测试。当前只有 STRIP 满足（`app/security/strip_detector.py`），Neural Cleanse 与 Activation Clustering 在 `app/security/` 下仅为 docstring 占位，对应工具仍是 Mock，导致 DoD 只满足 1/3。

## What Changes

- 实现可运行的 Neural Cleanse 检测算法（触发反演 + MAD 异常检测路径，无 torch 时走可注入 predictor 近似路径）。
- 实现可运行的 Activation Clustering 检测算法（中间层激活聚类/降维分析）。
- 将两者封装为正式 Tool（Adapter 模式，参照 `strip_tool.py`）并注册进 ToolRegistry。
- 保留现有 Mock 工具，用于无模型 / 快速演示 / CI 轻量场景。
- 新增真实算法的单元测试与一个可运行示例。

## Capabilities

### New Capabilities

- `detection-tools`: 内置后门检测工具（STRIP / Neural Cleanse / Activation Clustering）的契约、实现与运行行为，包括真实实现与 Mock 回退。

### Modified Capabilities

（无。本变更新增能力，不修改既有 capability 需求。）

## Impact

- 代码：`app/security/neural_cleanse.py`、`app/security/activation_clustering.py`（占位→实现）；`app/tools/`（新增 `neural_cleanse_tool.py`、`activation_clustering_tool.py`）。
- 测试：`tests/`（新增真实算法与工具契约测试）。
- API：`/health` 返回的已注册工具列表将新增真实工具。
- 依赖：可能引入 `numpy`（评分/聚类），`torch` 为可选、延迟导入。
- 与 PRD 关系：关闭 UTC-6 与 4.3 验收标准中未满足的 2/3。
