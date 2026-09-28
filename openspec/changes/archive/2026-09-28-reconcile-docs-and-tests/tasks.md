# Tasks

## 1. PRD 对账

- [x] 1.1 核对 PRD §7 完成度表并修正与代码不符的项（如 Report/Trace/API 现状），确认每条可被代码位置佐证
- [x] 1.2 修正 PRD §8 里程碑状态（M3 已完成、M4 已完成、M6 进行中）与 4.x 验收勾选，确认与现状一致

## 2. README / 中文文档

- [x] 2.1 修正根 `README.md` 与 `readme_Zh.md` 与实际实现不符处（工具状态、端点表、Production Path）
- [x] 2.2 明确 Docker"接口保留，本期不实现"，确认 Out of Scope 描述与 PRD 2.2 一致

## 3. 测试补强与回归

- [x] 3.1 汇总并核对各变更新增测试（真实 NC/AC、/replay、报告 CoT/审计、BFF 集成）已落地
- [x] 3.2 运行 `pytest tests/ -v` 全量回归，确认全绿并记录结果
