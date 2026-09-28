# Design

## Context

See proposal.md - Why. `app/memory/embedder.py` 已定义 `EmbedderLike` 协议（`embed` / `similarity`），注释明确预留替换为 OpenAI embedding。`configs/settings.py` 用 pydantic-settings 管理 `BACKDOOR_*`，`app/llm/` 已有 provider registry 可参照。

## Goals / Non-Goals

**Goals:**

- embedding provider 可插拔，配置即可切换；未配置时行为与现状一致（回退 hashing）。
- 鉴权/限流以中间件形式提供，默认关闭，开启后行为可测。

**Non-Goals:**

- 不做多租户、计费、角色权限模型。
- 不引入外部向量数据库（沿用当前内存 + JSON 持久化）。

## Decisions

- **D1：`Embedder` 抽象 + registry，仿 `app/llm/registry.py`。** provider：`hashing`（默认）与 `openai`。理由：与既有 LLM 抽象风格一致。
- **D2：真实 embedding 失败即回退 hashing 并告警。** 理由：不阻断检测流程，符合降级优先的既有设计。替代方案（硬失败）会降低可用性。
- **D3：鉴权用 API key 头校验，限流用令牌桶/固定窗口中间件。** 默认 `enabled=false`。理由：本地开发零配置；生产可开启。
- **D4：敏感信息不落盘。** embedding API key 仅从环境/配置读取，不写入 trace 或报告（NFR-5）。

## Risks / Trade-offs

- [真实 embedding 带来外部依赖与成本] → 默认关闭，按需开启；失败回退。
- [限流误伤本地调试] → 默认关闭，阈值可配。
- [向量维度不一致] → 切换 provider 时重建 L2 语义记忆，文档标注迁移要求。
