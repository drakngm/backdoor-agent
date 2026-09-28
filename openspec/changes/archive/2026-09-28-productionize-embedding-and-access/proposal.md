# Proposal

## Why

README Production Path #4 要求以真实 embedding 替换 hashing embedder，Production Path #6 要求鉴权与限流。当前 `app/memory/embedder.py` 为纯 Python 词袋哈希，语义检索质量受限；平台所有 API 无鉴权与限流，无法在受控/多用户环境使用。

## What Changes

- 新增可插拔的真实 embedding provider（如 OpenAI 兼容 `text-embedding-3-small`），并保留 hashing 作为默认回退。
- 语义记忆检索在配置了真实 provider 时走真实向量，否则回退 hashing。
- 为核心 API 增加鉴权与限流中间件（可配置开启；默认关闭以保持本地开发体验）。
- 新增 provider 选择、鉴权与限流的测试。

## Capabilities

### New Capabilities

- `semantic-memory`: 语义记忆的向量化与相似检索行为，含 provider 抽象与回退。
- `access-control`: 核心 API 的鉴权与限流行为。

### Modified Capabilities

（无。）

## Impact

- 代码：`app/memory/embedder.py`、`app/memory/semantic_memory.py`、`configs/settings.py`、`app/main.py`（中间件）。
- 配置：新增 embedding provider 与鉴权/限流相关配置项（`BACKDOOR_*`）。
- 测试：`tests/` 新增相关用例。
- 与 PRD 关系：Production Path #4/#6；PRD 2.2 曾将鉴权/限流列为非本期范围，本变更将其提升为可选能力（默认关闭）。
