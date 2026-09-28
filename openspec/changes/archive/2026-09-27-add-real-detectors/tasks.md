# Tasks

## 1. 契约与工具骨架

- [x] 1.1 参照 `app/tools/strip_tool.py` 新增 `NeuralCleanseTool` 骨架并注册，运行相关单测确认 `/health` 能列出该工具
- [x] 1.2 参照 `strip_tool.py` 新增 `ActivationClusteringTool` 骨架并注册，运行相关单测确认 `/health` 能列出该工具
- [x] 1.3 为两个工具的 input/output schema 与 manifest 编写契约测试（含非法输入被拒绝路径），运行测试通过

## 2. 真实算法实现

- [x] 2.1 在 `app/security/neural_cleanse.py` 实现触发反演 + MAD 判定，支持可注入 predictor；补单元测试（可运行近似路径）并通过
- [x] 2.2 在 `app/security/activation_clustering.py` 实现降维 + 聚类判定，支持可注入 predictor；补单元测试并通过
- [x] 2.3 接通工具与算法（Adapter 调用），补端到端测试：给定样本输入返回含 `is_backdoor`/`confidence_score`/`risk_level`/`artifact` 的 `ToolOutput`

## 3. 回退与集成

- [x] 3.1 校验 Mock 与真实工具输出结构一致（对照测试），确认可无差别替换
- [x] 3.2 验证 Workflow 的 deep/forensic 策略能并行调用新工具，且 `fast_scan` 不受影响（运行 workflow 测试）
- [x] 3.3 更新 `README.md` 检测工具状态表与 PRD 4.3 完成度，确认文档与实现一致
