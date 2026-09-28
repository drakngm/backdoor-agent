# Spec Delta

## Purpose

定义语义记忆的向量化与相似检索行为：支持可插拔的真实 embedding provider，并在不可用时安全回退到内置 hashing embedder。

## ADDED Requirements

### Requirement: Pluggable embedding provider

语义记忆 SHALL 支持通过配置选择 embedding provider；未配置或未指定时 SHALL 使用内置 hashing embedder，并在真实 provider 调用失败时回退到 hashing 而非中断。

#### Scenario: Default uses hashing embedder

- **WHEN** 未配置真实 embedding provider
- **THEN** 语义检索 SHALL 使用 hashing embedder，行为与现状一致

#### Scenario: Real provider selected

- **WHEN** 配置了真实 embedding provider 且调用成功
- **THEN** 语义检索 SHALL 使用该 provider 的向量进行相似度计算

#### Scenario: Provider failure falls back

- **WHEN** 真实 provider 调用失败
- **THEN** 系统 SHALL 回退到 hashing embedder 并记录告警，不中断检测流程
