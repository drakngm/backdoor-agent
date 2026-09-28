# Design

## Context

See proposal.md - Why. 参考现状：`app/security/strip_detector.py` 已提供纯 Python 的真实 STRIP，并通过"可注入 predictor"与具体模型解耦；`app/tools/strip_tool.py` 展示了 `ToolAdapter` 的封装形态。Neural Cleanse 与 Activation Clustering 在 `app/security/` 下仅占位，`app/tools/mock_neural_cleanse.py`、`mock_activation_clustering.py` 为 Mock。运行环境需兼容 Python 3.10+ 与 Windows 本地、无 GPU。

## Goals / Non-Goals

**Goals:**

- 以与 STRIP 一致的 Adapter 形态提供真实 NC/AC，可在无 GPU、无重依赖环境下运行并通过测试。
- 保持工具契约与输出字段一致，使真实/Mock 工具可互换。

**Non-Goals:**

- 不追求论文级检测精度，不做大规模模型性能调优。
- 不强制依赖 PyTorch；torch 为可选且延迟导入。
- 不改动 Agent / Workflow / 调度引擎代码（NFR-1）。

## Decisions

- **D1：沿用"可注入 predictor"模式。** 照搬 STRIP 的解耦方式：算法核心对抽象 predictor 操作；环境存在 torch 且提供真实模型时走梯度/激活路径，否则走可运行的近似路径。理由：保证 CI 与 Windows 本地可运行。替代方案（强制 PyTorch）会抬高环境门槛并与 NFR-6 冲突。
- **D2：新增 `NeuralCleanseTool` / `ActivationClusteringTool` 继承 `ToolAdapter` 并注册。** Mock 工具保留，命名与 Mock 区分，均出现在 `/health`。理由：NFR-1 零改动接入。
- **D3：输出统一 `ToolOutput`。** 结论归一到 `is_backdoor` / `confidence_score` / `risk_level`，证据放入 `artifact`（`ActivationMap` / `TriggerPattern` / `EntropyDistribution` 等类型）。
- **D4：参数设上限与超时。** `timeout_ms` 与迭代/样本上限可配置，使 `fast_scan` 不被真实算法拖慢。

## Risks / Trade-offs

- [无 torch 时精度下降] → 明确标注为可运行近似实现，接口预留真实算法替换路径。
- [算法耗时超 fast_scan 预算] → 设超时与上限参数，必要时在 fast 策略中跳过。
- [numpy 依赖引入] → 采用可选导入并给出纯 Python 回退，保持最小依赖。
