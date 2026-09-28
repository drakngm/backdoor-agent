# detection-tools Specification

## Purpose
定义平台内置后门检测工具（STRIP / Neural Cleanse / Activation Clustering）应具备的可观测行为：统一工具契约、标准化安全输出、真实检测能力与 Mock 回退。

## Requirements

### Requirement: Standardized detector tool contract

每个检测工具 SHALL 实现统一契约：声明 manifest（name / description / version / input_schema / output_schema / timeout_ms / requires_gpu / tags），接收继承自 `ToolInput` 的输入，返回继承自 `ToolOutput` 的输出；输出 SHALL 包含标准化字段 `confidence_score`、`risk_level` 与 `artifact`。

#### Scenario: Detector is registered and discoverable

- **WHEN** 一个实现了统一契约的检测工具被注册到 ToolRegistry
- **THEN** 它 SHALL 出现在 `/health` 的工具列表中，并可被 Agent 与 Workflow 调用

#### Scenario: Invalid input is rejected

- **WHEN** 调用方传入缺失必需字段的输入
- **THEN** 工具 SHALL 返回校验失败（ToolValidationError），且不执行算法主体

### Requirement: Real Neural Cleanse detection

平台 SHALL 提供一个真实（非 Mock）Neural Cleanse 检测工具，基于触发反演与 MAD 异常检测判定模型是否含后门，并输出标准化风险结论。当运行环境无 torch 时，SHALL 通过可注入 predictor 的近似路径仍可运行。

#### Scenario: Detect on a candidate model

- **WHEN** 对给定模型路径发起 Neural Cleanse 检测
- **THEN** 结果 SHALL 包含 `is_backdoor`、`confidence_score`、`risk_level` 与可追溯 artifact（含类型/哈希等元数据）

#### Scenario: Model unavailable fails gracefully

- **WHEN** 模型路径不存在或不可加载
- **THEN** 工具 SHALL 返回 `success=false` 及可读错误信息，而非抛出未捕获异常

### Requirement: Real Activation Clustering detection

平台 SHALL 提供一个真实（非 Mock）Activation Clustering 检测工具，基于中间层激活的降维与聚类分析判定模型是否含后门，并输出标准化风险结论。

#### Scenario: Detect on a candidate model

- **WHEN** 对给定模型路径发起 Activation Clustering 检测
- **THEN** 结果 SHALL 包含 `is_backdoor`、`confidence_score`、`risk_level` 与可追溯 artifact

#### Scenario: Insufficient activations are handled

- **WHEN** 可用激活样本不足以支撑聚类
- **THEN** 工具 SHALL 返回明确的不确定结论（低置信度或 `success=false`）而非崩溃

### Requirement: Mock fallback preserved

平台 SHALL 保留 Mock 检测工具；Mock 与真实工具 SHALL 在契约与输出结构上保持一致，以便在无模型或快速演示场景下无差别替换。

#### Scenario: Mock and real tools are interchangeable

- **WHEN** 通过统一调用入口分别调用 Mock 与真实工具
- **THEN** 两者 SHALL 返回结构一致的 `ToolOutput`，仅在数值与结论上不同
