# web-console Specification

## Purpose
定义 Web 指挥中心（BFF + 前端）与核心平台之间的数据联通契约：优先使用核心真实数据、可配置降级、并向用户透明标注数据来源。

## Requirements

### Requirement: Prefer core data with visible fallback

Web 指挥中心 SHALL 在核心 API 可用时展示核心真实数据；当核心不可用且允许降级时 SHALL 回退到仿真数据，且每个数据响应 SHALL 标注来源为 `core` 或 `mock`。

#### Scenario: Core available serves real data

- **WHEN** 核心 API 可达
- **THEN** BFF 读模型响应 SHALL 返回核心数据且 `source = core`

#### Scenario: Core unavailable falls back to mock

- **WHEN** 核心 API 不可达且 `ALLOW_MOCK_FALLBACK` 为真
- **THEN** BFF 响应 SHALL 返回仿真数据且 `source = mock`，且不返回 5xx

#### Scenario: Fallback disabled surfaces error

- **WHEN** 核心 API 不可达且 `ALLOW_MOCK_FALLBACK` 为假
- **THEN** BFF SHALL 返回明确的错误响应，而不是静默返回仿真数据

### Requirement: Frontend reflects data provenance

前端 SHALL 依据响应中的来源标注展示"真实/仿真"状态，使用户可区分真实检测结果与仿真数据。

#### Scenario: Provenance indicator shown

- **WHEN** 某面板的数据 `source = mock`
- **THEN** 该面板 SHALL 显示仿真数据标识
