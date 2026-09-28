# Spec Delta

## Purpose

定义核心 API 的访问控制行为：可配置的鉴权与限流，默认关闭以保持本地开发零配置，开启后按配置拒绝未授权或超额请求。

## ADDED Requirements

### Requirement: Configurable API authentication

核心 API SHALL 支持可配置的鉴权；当鉴权开启时，未携带有效凭据的请求 SHALL 被拒绝。

#### Scenario: Auth disabled by default

- **WHEN** 未开启鉴权
- **THEN** 请求 SHALL 按现有行为被处理，不要求凭据

#### Scenario: Unauthorized request rejected

- **WHEN** 鉴权开启且请求缺少或携带无效凭据
- **THEN** 系统 SHALL 返回 401/403，且不执行检测逻辑

### Requirement: Configurable rate limiting

核心 API SHALL 支持可配置的限流；当限流开启时，超过阈值的请求 SHALL 被限制。

#### Scenario: Over-limit request throttled

- **WHEN** 限流开启且某客户端在窗口内超过阈值
- **THEN** 系统 SHALL 返回 429
