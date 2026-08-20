# PRD — AI 后门检测 Agent 平台

| 字段 | 内容 |
|------|------|
| 文档版本 | v0.1 (Draft) |
| 状态 | 待评审 |
| 技术栈 | Python 3.10+ / FastAPI / Pydantic v2 / asyncio / LLM / PyTorch |
| 部署 | 本地开发为主，Docker 接口预留（本期不实现） |
| 关联文档 | `README.md`（架构）、`configs/agent.yaml`（运行时配置）、`pyproject.toml` |

---

## 1. 背景与目标

### 1.1 问题陈述
STRIP、Neural Cleanse、Activation Clustering 等 AI 安全检测工具各自独立、接口各异，缺乏统一编排。安全分析人员需手动串联多个工具，效率低，且分析过程不可追溯、不可复现。

### 1.2 产品目标
将多种后门检测算法统一封装为**可插拔工具模块**，由一个 **Hybrid Agent** 自动编排，实现：

1. **自动化编排**：Agent 根据模型架构与初始检测结果自主决策工具选择与执行顺序。
2. **确定性执行**：DAG Workflow 保证执行路径确定、可复现。
3. **可追溯审计**：全链路四级 Trace + 结构化推理链（CoT），支持完整回放与事后审计。
4. **可扩展**：新增检测算法只需实现统一接口并注册，不改动调度引擎。

### 1.3 成功标准（DoD）
- 一个从未接入的新检测算法，通过实现 `BaseTool` + 注册即可接入，无需改动 Agent / Workflow / 调度引擎代码。
- 一次检测流程可完整回放：能看到每一步的推理（CoT）、每个工具调用、数据流转、最终决策依据。
- Agent 能基于“模型架构 + 初始检测结果”动态决定后续调用哪些工具（而非固定脚本）。

---

## 2. 范围

### 2.1 本期范围（In Scope）
1. Hybrid Agent 架构（Agent Loop + DAG Workflow）
2. Agent Runtime（Tool Calling / Context Management / Pre-Post Hook）
3. Unified Tool Contract（Manifest + 标准化 Artifact + Adapter 模式）
4. Hierarchical Memory System（短期滑窗 / 中期语义 / 长期规则）
5. Execution Trace & Audit（系统级 / 数据级 / 决策级 / 审计级）

### 2.2 非本期范围（Out of Scope）
- **Docker 部署**：保留 `docker/Dockerfile`、`docker/docker-compose.yml` 接口，暂不验证与完善。
- Redis / Celery 异步任务队列：保留 `scripts/init_redis.py` 与 `configs.settings.redis_*` 占位。
- 真实检测算法的精度调优（PyTorch 训练/推理工程化）。
- 鉴权、限流、多租户、计费。

### 2.3 目标用户
- **安全分析人员**：提交模型 → 获得检测报告与完整审计链。
- **算法工程师**：接入新检测算法（实现统一接口即可）。
- **平台/DevOps 工程师**：CI/CD 中作为门禁调用 `fast_scan`。

---

## 3. 总体架构（目标态）

```
┌────────────────────────────────────────────────────────────┐
│                    FastAPI Entry Layer                      │
│       /health   /run_agent   /run_workflow   /replay       │
└──────────────┬──────────────────────────────┬──────────────┘
               │                              │
      ┌────────▼─────────┐          ┌─────────▼──────────┐
      │  Agent Mode       │          │  Workflow Mode      │
      │  AgentLoop (LLM)  │◄─动态生成─┤  Planner → DAG      │
      │  ToolRouter       │          │  Executor(并行tier) │
      │  HookManager      │          │  Strategies         │
      └────────┬──────────┘          └─────────┬──────────┘
               │                               │
               └───────────────┬───────────────┘
                               ▼
              ┌────────────────────────────────┐
              │        Unified Tool Layer       │
              │  ToolManifest / ToolContract    │
              │  Adapter (算法→Tool 封装)        │
              │  Artifact Model (标准化产物)      │
              │  ToolRegistry (插件注册)          │
              └────────────────────────────────┘
                               │
        ┌──────────────────────┼───────────────────────┐
        ▼                      ▼                        ▼
 Hierarchical Memory      Execution Trace            Report
 (短期/中期/长期)          (系统/数据/决策/审计)        Generator
```

---

## 4. 功能需求

### 4.1 Hybrid Agent 架构

**目标**：Agent Loop 负责高层推理与策略决策；DAG Workflow 负责确定性编排执行。Agent 基于“模型架构 + 初始检测结果”自主决策工具选择与执行顺序，DAG 保证可复现。

#### 需求明细
| 编号 | 需求 | 优先级 |
|------|------|--------|
| HA-1 | Agent 在收到请求后，先分析模型元信息（架构、层数、类别数等），产出**检测计划草案** | P0 |
| HA-2 | Agent 执行“初始检测”（如 fast 阶段）后，**基于结果动态决定**后续调用哪些检测工具（而非固定脚本） | P0 |
| HA-3 | 决策结果可**转化为 TaskGraph DAG** 交给 Workflow 确定性执行 | P0 |
| HA-4 | 同一输入 + 同一决策快照 → 完全一致的 DAG（可复现） | P1 |
| HA-5 | 保留纯 Workflow 模式（指定 strategy 直接执行，不走 LLM） | P1 |
| HA-6 | 三种策略 `fast_scan` / `deep_scan` / `forensic_scan` 作为预置 DAG 模板 | P1 |

#### 当前状态
- `app/agents/agent_loop.py`：循环骨架已实现，但 `MockLLM` 硬编码返回固定调用序列。
- `app/workflow/`：`Planner`/`TaskGraph`/`WorkflowExecutor` 骨架完整，策略为静态 DAG 模板。
- **Gap**：Agent 与 Workflow 之间缺少“动态生成 DAG”的桥接（Agent 决策 → 构建 TaskGraph 的接口不存在）。

#### 验收标准
- [ ] 接入真实 LLM 后，`/run_agent` 能对同一请求产生不同执行路径（依据模型/初始结果）。
- [ ] 存在接口 `AgentLoop` 可将决策转换为 `TaskGraph` 并交给 `WorkflowExecutor` 执行。
- [ ] 给定相同 `trace_id` 与决策快照，重建的 DAG 拓扑一致。

---

### 4.2 Agent Runtime

**目标**：实现 Tool Calling、Context Management、Pre/Post Hook 三大运行时能力。

#### 需求明细
| 编号 | 需求 | 优先级 |
|------|------|--------|
| AR-1 | Tool Calling：LLM 输出结构化 `tool_call`，经 Router 校验/执行/超时控制 | P0 |
| AR-2 | Context Management：滑窗式上下文，接近真实的 token 计数与裁剪策略 | P0 |
| AR-3 | Pre-Hook：工具执行前的输入校验、参数规范化、权限/限额检查 | P0 |
| AR-4 | Post-Hook：工具执行后的结果校验、结构化验证、缓存 | P1 |
| AR-5 | Error-Hook：工具失败时的降级、重试、告警 | P1 |
| AR-6 | Loop 超时/最大迭代保护，可配置 | P1 |

#### 当前状态
- `app/agents/tool_router.py`：Tool Calling 完整（校验→构建→超时执行→输出校验）。
- `app/memory/working_memory.py`：滑窗已实现，但 token 估算为“每 4 字符 ≈ 1 token”的粗估。
- `app/agents/hooks.py`：`HookManager` 生命周期完整，但内置 hook 仅打日志（占位）。
- **Gap**：Pre/Post Hook 无真实校验逻辑；token 管理精度不足；LLM 未接入（Mock）。

#### 验收标准
- [ ] `ToolRouter.route` 对非法输入返回 `ToolValidationError`，超时返回 `ToolTimeoutError`。
- [ ] Pre-Hook 可拦截非法输入（如缺少必需字段）并阻止工具执行。
- [ ] Post-Hook 可对输出做二次校验并可在失败时改写/丢弃结果。
- [ ] 上下文在超限时正确裁剪最旧消息（保留 system 消息）。

---

### 4.3 Unified Tool Contract

**目标**：统一工具契约层 = Tool Manifest + 标准化 Artifact Model + Adapter 模式。新增算法零改动接入。

#### 需求明细
| 编号 | 需求 | 优先级 |
|------|------|--------|
| UTC-1 | Tool Manifest：工具元数据（name/description/version/input-schema/output-schema/timeout/GPU/tags） | P0 |
| UTC-2 | 标准化 Artifact Model：产物统一建模（类型、路径、哈希、大小、格式），而非松散 dict | P0 |
| UTC-3 | Adapter 模式：将外部/第三方算法适配为 `BaseTool`，隔离算法内部细节 | P0 |
| UTC-4 | 插件注册：实现 `BaseTool` 并 `registry.register()` 即可接入 | P0 |
| UTC-5 | 输入/输出 schema 强校验（Pydantic），输出含 `confidence_score` / `risk_level` 标准化字段 | P0 |
| UTC-6 | 真实算法落地：`app/security/` 中的占位实现接入为正式 Tool | P1 |

#### 当前状态
- `app/tools/contract.py`：`ToolContract`（Manifest 雏形）已实现。
- `app/tools/schemas.py`：`ToolInput`/`ToolOutput` 含标准化安全字段，但 `artifact` 为松散 `dict`。
- `app/tools/base.py`：`BaseTool` 抽象基类已实现。
- `app/tools/mock_*.py`：3 个 Mock 检测工具已实现。
- `app/security/`：仅 docstring 占位，无真实算法。
- **Gap**：无 Adapter 模式；`artifact` 未建模为标准化类；真实算法未实现。

#### 验收标准
- [ ] 定义 `Artifact` 模型（含 `type`/`path`/`hash`/`size`/`format` 等字段），`ToolOutput.artifact` 使用之。
- [ ] 存在 `ToolAdapter` 基类，可将任意算法函数包装为 `BaseTool`。
- [ ] 一个仅实现 `BaseTool` 的新工具，`register()` 后能在 `/health` 列出并被 Agent/Workflow 调用。
- [ ] STRIP / Neural Cleanse / Activation Clustering 有真实（或可运行）实现并通过测试。

---

### 4.4 Hierarchical Memory System

**目标**：三层记忆架构——短期会话记忆（滑窗，支持即时追问）、中期语义记忆（向量化，支持跨工具关联发现）、长期规则记忆（积累验证过的检测策略），模拟记忆巩固过程。

#### 需求明细
| 编号 | 需求 | 优先级 |
|------|------|--------|
| MEM-1 | 短期记忆：滑窗式会话上下文，支持即时追问（多轮对话） | P0 |
| MEM-2 | 中期语义记忆：向量化存储，支持语义检索与**跨工具关联发现**（如“某模型指纹曾触发 STRIP 与 AC 双告警”） | P0 |
| MEM-3 | 长期规则记忆：积累**验证过的检测策略/规则**，供 Agent 复用 | P1 |
| MEM-4 | 记忆巩固：短期 → 中期 → 长期的衰减/提升机制（MVP 可简化） | P2 |
| MEM-5 | 降级检索：命中失败时逐层回退 | P1 |

#### 当前状态
- `app/memory/`：现有 4 层 `Working` / `Session` / `Project` / `Knowledge`。
  - `WorkingMemory`：滑窗 ✅（对应短期）
  - `SessionMemory`：完整会话历史 ✅（并入短期）
  - `ProjectMemory`：JSON 持久化报告/模型指纹 ✅（对应中期/长期雏形）
  - `KnowledgeMemory`：硬编码文档 + 关键词匹配 ❌（未向量化，非语义）
- **Gap**：需将 4 层重映射为 3 层；语义记忆缺向量化与跨工具关联；规则记忆缺失；巩固机制缺失。

#### 验收标准
- [ ] 记忆层明确映射为三层（短期/中期/长期），`ContextManager` 接口一致。
- [ ] 中期记忆支持向量相似检索（可用本地向量库或 `numpy` 余弦近似），并支持跨工具关联查询。
- [ ] 长期记忆可存储/检索“检测策略规则”，Agent 可引用历史验证过的策略。
- [ ] 多轮追问：第二次请求能引用上一次会话上下文。

---

### 4.5 Execution Trace & Audit

**目标**：多粒度全链路追踪（系统级/数据级/决策级/审计级四级），每次决策输出结构化推理链（CoT），支持完整回放与事后审计。

#### 需求明细
| 编号 | 需求 | 优先级 |
|------|------|--------|
| ET-1 | 系统级 Trace：进程/耗时/span 树（已具备，需保留） | P0 |
| ET-2 | 数据级 Trace：记录每个工具输入/输出、产物 hash、数据流转（tool A 输出 → tool B 输入） | P0 |
| ET-3 | 决策级 Trace：结构化 CoT 推理链（每步决策的 reasoning/依据/候选方案） | P0 |
| ET-4 | 审计级 Trace：不可变审计日志（谁/何时/对哪个模型/执行了什么/结论） | P1 |
| ET-5 | 回放：根据 trace_id 重建完整执行流程（时间线 + 决策链 + 数据流） | P1 |
| ET-6 | 可视化：Mermaid 流程 + 决策链/数据流视图 | P1 |

#### 当前状态
- `app/core/execution_trace.py`：span 树（近似系统级）完整，支持 Mermaid/火焰图/关键路径。
- `MockLLM` 有 `reasoning` 字段，但非结构化 CoT，未单独建模。
- **Gap**：无数据级/决策级/审计级 Trace；无 CoT 结构化模型；无回放接口；无持久化审计日志。

#### 验收标准
- [ ] 定义四级 Trace 的数据模型，并与现有 `ExecutionTrace` 集成。
- [ ] LLM 决策产出结构化 `CoTStep`（reasoning/evidence/candidates/decision）。
- [ ] 每次工具调用的输入/输出/产物 hash 被记录，可追溯数据流转。
- [ ] 提供 `/replay/{trace_id}` 端点或等价函数，返回完整审计链。
- [ ] 审计日志持久化（落盘 JSON，MVP 即可）。

---

## 5. 非功能需求

| 编号 | 类别 | 需求 |
|------|------|------|
| NFR-1 | 可扩展性 | 新增检测工具不改调度引擎代码，仅实现接口 + 注册 |
| NFR-2 | 可复现性 | 相同输入 + 决策快照 → 相同执行路径与可复现结果 |
| NFR-3 | 可观测性 | 全链路 Trace + 结构化日志（trace_id 贯穿） |
| NFR-4 | 性能 | `fast_scan` 目标 ≤ 30s；并行 tier 工具并发执行 |
| NFR-5 | 安全 | 不落盘/不记录 API key 与敏感凭据 |
| NFR-6 | 兼容性 | Python 3.10+；Windows 本地可运行（`asyncio` 兼容） |

---

## 6. 关键接口与数据模型（约定）

### 6.1 Tool 接入契约（目标态）
```python
class MyNewDetector(ToolAdapter):
    manifest = ToolManifest(
        name="my_detector",
        description="...",
        version="1.0.0",
        input_schema=MyInput,      # 继承 ToolInput
        output_schema=MyOutput,    # 继承 ToolOutput
        timeout_ms=60000,
        requires_gpu=False,
        tags=["detection", "deep_scan"],
    )
    async def run(self, input: MyInput) -> MyOutput:
        ...  # 算法核心
```
> 接入 = 实现 `run` + `manifest` + `registry.register(MyNewDetector())`，即完成。

### 6.2 Artifact 模型（目标态）
```python
class Artifact(BaseModel):
    type: str            # activation_map / trigger_pattern / entropy_dist / ...
    path: Optional[str]
    hash: Optional[str]  # sha256
    size_bytes: Optional[int]
    format: Optional[str]  # npy / png / json / ...
    metadata: dict = {}
```

### 6.3 CoT 推理链（目标态）
```python
class CoTStep(BaseModel):
    step_index: int
    reasoning: str              # 自然语言推理
    evidence: list[dict]        # 依据（工具结果引用）
    candidates: list[str]       # 候选方案
    decision: str               # 最终决策（调用某工具 / 结束 / 切换策略）
    confidence: float
```

### 6.4 四级 Trace 关系
```
系统级 span 树 (ExecutionTrace)
  └─ 数据级 dataflow（tool input/output/artifact hash）
       └─ 决策级 CoT steps（挂载在 LLM span 上）
            └─ 审计级 audit log（持久化、不可变）
```

---

## 7. 完成度评估（现状快照）

| 模块 | 文件 | 完成度 | 说明 |
|------|------|--------|------|
| Agent Loop | `app/agents/agent_loop.py` | 85% | LLM 抽象化，可注入任意 provider；决策闭环待 M3 |
| Tool Router | `app/agents/tool_router.py` | 85% | Tool Calling 完整 |
| Hook | `app/agents/hooks.py` | 85% | 决策模型 + 真实校验逻辑（PreToolUse 输入校验 / PostToolUse 结果验证）落地 |
| LLM Provider | `app/llm/*` | 85% | LLMClient 抽象 + registry + mock/openai/anthropic 三实现 |
| Tool Contract | `app/tools/contract.py` | 90% | Manifest 别名 + Adapter 模式 |
| Tool Base/Schema | `app/tools/base.py` `schemas.py` | 90% | Artifact 标准化为 `list[Artifact]` |
| Registry | `app/tools/registry.py` | 95% | 完整 |
| Mock Tools | `app/tools/mock_*.py` | 80% | 3 个可用 Mock |
| 真实算法 | `app/security/*.py` | 40% | STRIP 已实现（纯 Python）+ STRIPTool；NC/AC 待实现 |
| Workflow | `app/workflow/*` | 85% | DAG/策略/执行完整 |
| Planner | `app/workflow/planner.py` | 85% | 静态策略选择 |
| Memory | `app/memory/*` | 75% | 上下文管理优化 + 确定性摘要；向量化/三层重映射待 M4 |
| Trace | `app/core/execution_trace.py` | 65% | 仅系统级 span 树 |
| Report | `app/report/generator.py` | 80% | 聚合可用，未接 CoT/审计 |
| API | `app/api/*` | 85% | 三端点完整，缺 /replay |
| Docker | `docker/*` | 30% | 接口预留，本期不实现 |

---

## 8. 里程碑与迭代计划

### M1 — 契约层夯实（Tool Contract + Adapter + Artifact）✅ 已完成
- 标准化 `Artifact` 模型，改造 `ToolOutput`。
- 新增 `ToolAdapter` 抽象，把 `app/security/` 的算法接为 Tool。
- 实现至少 1 个真实算法（STRIP 优先）。
- 验收：新工具零改动接入 + 通过 schema 校验测试。

### M2 — Agent Runtime 增强（LLM + Hook + Context）✅ 已完成
- 接入真实 LLM Provider 抽象（`LLMClient` 接口，OpenAI/Anthropic 适配）。
- Pre/Post Hook 落地真实校验逻辑。
- 改进 token 计数与滑窗裁剪。
- 验收：Agent 能真实推理并调用工具；Hook 能拦截/改写。

### M3 — Hybrid 决策闭环（Agent → 动态 DAG）🔄 下一步
- 实现“Agent 决策 → 构建 TaskGraph”桥接。
- Agent 基于模型元信息 + 初始检测结果动态选工具/定顺序。
- 保留纯 Workflow 模式与预置策略。
- 验收：`/run_agent` 可产生非固定执行路径，且可转 DAG 确定性执行。

### M4 — 记忆系统重构（三层 + 向量化）
- 重映射为短期/中期/长期三层。
- 中期语义记忆向量化（本地向量方案）+ 跨工具关联发现。
- 长期规则记忆落地。
- 验收：多轮追问可用；跨工具关联可检索。

### M5 — Trace & Audit 完善（四级 + CoT + 回放）
- 定义四级 Trace 模型并集成。
- 结构化 CoT 推理链建模。
- 审计日志持久化 + `/replay/{trace_id}` 回放端点。
- 验收：完整回放一次检测流程的决策链与数据流。

### M6 — 收尾（Docker 接口确认 + 文档 + 全量测试）
- 确认 Docker 文件接口保留、可后续补全（本期不实现）。
- 补全单测/集成测试，跑通 `pytest tests/ -v`。

---

## 9. 风险与开放问题

| # | 风险/问题 | 影响 | 缓解/备注 |
|---|-----------|------|-----------|
| 1 | 真实 LLM API 依赖外部服务（无 key 无法联调） | 阻塞 M2/M3 | 保留 MockLLM 作为默认，LLMClient 接口可注入 |
| 2 | 真实检测算法（PyTorch）实现周期长 | 阻塞 M1 | 优先 Mock→Adapter 解耦，算法可后续迭代替换 |
| 3 | 语义记忆向量化方案选型（本地 vs 外部向量库） | 阻塞 M4 | MVP 用 `numpy` 余弦近似，接口预留可替换 |
| 4 | 现有 4 层记忆 → 3 层重映射的兼容性 | 改动面 | 保留 `ContextManager` 统一入口，内部重映射 |
| 5 | Windows 下 `asyncio`/文件路径兼容 | 运行稳定 | 全部用 `pathlib`，避免 Unix-only 命令 |
| 6 | “可复现”与“LLM 随机性”天然冲突 | 需求冲突 | 通过决策快照冻结 + 确定性 DAG 执行缓解 |

---

## 10. 术语表

| 术语 | 说明 |
|------|------|
| STRIP | STRong Intentional Perturbation，基于扰动熵的后门检测 |
| Neural Cleanse | 反向工程触发器 + MAD 异常检测 |
| Activation Clustering | 中间层激活聚类（PCA/t-SNE + K-Means）检测异常 |
| Tool Manifest | 工具的元数据契约（等价于现有 `ToolContract`） |
| Adapter | 将外部算法适配为统一 `BaseTool` 的包装层 |
| CoT | Chain-of-Thought，结构化推理链 |
| Hybrid Agent | Agent Loop（高层推理）+ DAG Workflow（确定性编排）混合架构 |
| Trace 四级 | 系统级 / 数据级 / 决策级 / 审计级 |

---

## 11. 附：现有代码到 PRD 的映射速查

| 现有文件 | 对应 PRD 需求 |
|----------|--------------|
| `app/agents/agent_loop.py` | HA-1~4, AR-6 |
| `app/agents/tool_router.py` | AR-1 |
| `app/agents/hooks.py` | AR-3~5 |
| `app/llm/*` | AR（LLM Provider 抽象） |
| `app/tools/contract.py` | UTC-1 |
| `app/tools/schemas.py` | UTC-2, UTC-5 |
| `app/tools/base.py` | UTC-3, UTC-4 |
| `app/tools/adapter.py` | UTC-3（Adapter 模式） |
| `app/tools/registry.py` | UTC-4 |
| `app/tools/strip_tool.py` | UTC-6（真实 STRIP Tool） |
| `app/security/strip_detector.py` | UTC-6（真实算法） |
| `app/workflow/*` | HA-3~6 |
| `app/memory/*` | MEM-1~5 |
| `app/core/execution_trace.py` | ET-1, ET-6 |
| `app/core/trace.py` `logging.py` | NFR-3 |
| `app/report/generator.py` | 报告产出（关联 ET-4） |
| `docker/*` `scripts/init_redis.py` | Out of Scope（接口保留） |
