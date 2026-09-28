# Tasks

## 1. 报告扩展

- [x] 1.1 `ReportGenerator.generate` 新增可选 trace 入参并输出 `decision_chain`，补单测（含 CoT 步骤）通过
- [x] 1.2 输出 `audit`（含 `verified`）与 `data_flow_summary`，补单测断言字段存在与结构正确
- [x] 1.3 无 trace 时优雅降级并标注证据不完整，补单测通过

## 2. 调用方接通

- [x] 2.1 `Dispatcher` / hybrid 流程在生成报告时传入四级 trace，补集成测试：报告含 decision_chain 与 audit
- [x] 2.2 校验既有报告消费方（API 响应）向后兼容，运行相关测试通过

## 3. 文档

- [x] 3.1 更新 `README.md` 报告字段说明与 PRD §7 Report 完成度，确认与实际一致
