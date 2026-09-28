# 🔒 AI 后门检测与防御 Agent 系统

> **用于深度学习模型自动化后门检测的混合型 AI Agent。**

结合 **Agent Loop**（高层推理与检测策略决策）与 **DAG Workflow**（确定性工具编排）、
**统一工具契约**、**三层分层记忆** 以及 **四级 Trace 系统**，实现完整的可解释性与可审计性。

---

## 🏗 架构

```
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI 入口层                             │
│    /health   /run_agent   /run_workflow   /run_hybrid        │
└───────────────┬──────────────┬──────────────┬────────────────┘
                │              │              │
      ┌─────────▼────┐  ┌──────▼──────┐  ┌────▼─────────────┐
      │  Agent 模式   │  │ Workflow 模式│  │  Hybrid 模式      │
      │  agent_loop  │  │ planner + DAG│  │  决策引擎          │
      │  tool_router │  │ executor     │  │  -> DAG 编译器    │
      │  hooks       │  │ strategies   │  │  -> executor      │
      └───────┬───────┘  └──────┬───────┘  └────────┬────────┘
              │                 │                   │
              └────────────┬────┴───────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │          共享工具层                    │
        │  ToolContract / ToolAdapter / Artifact│
        │  ToolRegistry + Mock/真实检测器        │
        └──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────────┐
        ▼                  ▼                       ▼
   LLM Provider      分层记忆                四级 Trace
   (mock/openai/     (情景/语义/程序化          (系统/数据/决策
    anthropic)        + 记忆固化)               /审计 + CoT + 回放)
```

## 🔑 核心特性

- **Hybrid Agent 架构**：Agent Loop（LLM/规则驱动推理）+ DAG Workflow（确定性执行）。
  Agent 根据模型元信息与中间结果自主决策工具选择与执行顺序；每个决策编译成 DAG 节点。
- **三种执行模式**：Agent（`/run_agent`）、Workflow（`/run_workflow`）、Hybrid（`/run_hybrid`）
- **LLM Provider 抽象**：`LLMClient` 接口，内置 mock / OpenAI / Anthropic 实现
  （OpenAI 兼容端点如 DeepSeek 可通过 `.env` 直接使用）
- **统一工具契约**：`ToolContract`（清单）+ `ToolAdapter`（适配器模式）+
  标准化 `Artifact` 模型——新检测器只需实现统一接口即可接入
- **Pre/Post Hook 校验**：基于决策的钩子（allow/deny），实现输入校验（PreToolUse）
  与结果验证（PostToolUse）
- **三层分层记忆**：情景记忆（Redis 滑窗）→ 语义记忆（向量）→ 程序化记忆（规则），
  并带有记忆固化（巩固）机制
- **四级 Trace**：系统 span → 数据流（哈希）→ 决策 CoT → 不可变审计日志（哈希链），
  支持回放与跨 Trace 对比
- **标准化安全输出**：`confidence_score`、`risk_level`（LOW/MEDIUM/HIGH）、产物 Artifact

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# （可选）在 .env 中配置 LLM Provider
#   BACKDOOR_LLM_PROVIDER=openai
#   BACKDOOR_LLM_API_BASE_URL=https://opencode.ai/zen/go/v1
#   BACKDOOR_LLM_API_KEY=sk-...
#   BACKDOOR_LLM_MODEL=deepseek-v4-flash

# 启动开发服务器
python scripts/run_dev.py
```

API 访问地址：`http://localhost:8000/docs`

### API 端点

| 方法 | 路径 | 说明 |
|--------|------|-------------|
| `GET` | `/health` | 系统健康状态 + 已注册工具 + 策略 |
| `POST` | `/run_agent` | Agent 模式：LLM → 工具 → 观察循环 |
| `POST` | `/run_workflow` | Workflow 模式：Planner → DAG → 并行执行 |
| `POST` | `/run_hybrid` | Hybrid 模式：Agent 决策 → DAG → 报告 |
| `GET` | `/replay/{trace_id}` | 回放已持久化的 Trace（完整审计链：决策 + 数据流 + 审计） |

### 示例：Hybrid 模式（Agent 决策 + DAG 执行）

```bash
curl -X POST http://localhost:8000/run_hybrid \
  -H "Content-Type: application/json" \
  -d '{"message": "检测一个 ResNet-18 模型中是否存在后门", "model_path": "resnet18.h5"}'
```

响应包含：
- `verdict` / `confidence` / `final_answer`：最终检测结论
- `decisions`：Agent 的决策链（工具 + 参数 + `depends_on`）
- `tool_results`：标准化工具输出（风险等级、置信度、is_backdoor）
- `report`：聚合报告，含 `decision_chain`（CoT）+ `audit`（verified）+ `data_flow_summary`
- `trace`：四级 Trace 回放——`decisions`（CoT）、`data_flow`（哈希）、`audit`
- `memory_consolidation`：L1→L2→L3 固化计数
- `mermaid`：执行流程可视化

## 📁 项目结构

```
backdoor-agent/
├── app/
│   ├── main.py                  # FastAPI 入口
│   ├── entry/dispatcher.py      # agent / workflow / hybrid 模式分发
│   ├── api/                     # REST 端点（health, agent, workflow, hybrid）
│   ├── agents/                  # Agent 运行时（agent_loop, tool_router, hooks）
│   ├── hybrid/                  # Hybrid Agent（model_analyzer, decision_engine, compiler）
│   ├── llm/                     # LLM Provider 抽象（base, registry, mock/openai/anthropic）
│   ├── workflow/                # Workflow 引擎（planner, task_graph, executor）
│   │   └── strategies/          # 扫描策略（fast/deep/forensic）
│   ├── tools/                   # 工具层（contract, base, adapter, registry, mocks）
│   ├── memory/                  # 分层记忆（episodic/semantic/procedural + 固化）
│   ├── trace/                   # 四级 Trace（models, audit, trace, hooks）
│   ├── core/                    # 全局基础设施（config, execution_trace, exceptions, logging）
│   ├── security/                # 检测算法实现
│   └── report/                  # 报告生成器
├── configs/                     # YAML + Python 配置（pydantic-settings）
├── tests/                       # pytest 测试套件
├── docker/                      # Docker 与 docker-compose（接口预留）
├── scripts/                     # 开发脚本（run_dev, init_redis）
├── web/                         # Web 指挥中心（React 前端 + FastAPI BFF，优先核心 + mock 回退）
├── PRD.md                       # 产品需求与里程碑状态
└── README.md
```

## 🧪 运行测试

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v --asyncio-mode=auto
```

## 🛠 技术栈

- **Python 3.10+**
- **FastAPI** — 异步 REST API
- **Pydantic v2** — Schema 校验
- **asyncio** — 并发执行
- **Redis** — L1 情景记忆（可选，自动降级为内存实现）
- **哈希向量器** — 零依赖文本向量（可插拔替换为 `text-embedding-3-small`）
- **Docker** — 接口预留（本期未实现）

## 🔒 检测工具

| 工具 | 说明 | 状态 |
|------|-------------|--------|
| `strip_detect` | STRIP：基于扰动熵的后门检测 | Mock（随机） |
| `neural_cleanse` | Neural Cleanse：触发器逆向 + MAD | Mock |
| `activation_clustering` | Activation Clustering：PCA/t-SNE + K-Means | Mock |
| `strip_detect_real` | 真实 STRIP 算法（纯 Python，可注入预测器） | 真实实现 |
| `neural_cleanse_real` | 真实 Neural Cleanse：触发器逆向 + MAD 异常检测（纯 Python） | 真实实现 |
| `activation_clustering_real` | 真实 Activation Clustering：激活 K-Means + silhouette（纯 Python） | 真实实现 |

对应算法原型见 `app/security/`，真实算法通过 `ToolAdapter` 封装为标准 Tool。

## 📊 扫描策略

| 策略 | 工具 | 时长 | 适用场景 |
|----------|-------|----------|----------|
| `fast_scan` | 仅 STRIP | ~30s | CI/CD 流水线门禁 |
| `deep_scan` | STRIP + NC + AC（并行） | ~5min | 发布前模型审计 |
| `forensic_scan` | 全部检测器 | ~30min | 安全事件取证调查 |

## 🧠 记忆架构

```
L1 情景记忆（短期）   →  Redis 滑窗（N=20），关键词匹配，会话级
L2 语义记忆（中期）   →  向量化发现（哈希向量器），语义检索，
                        跨会话持久化（JSON）
L3 程序化记忆（长期） →  结构化规则 + 向量化案例库，策略匹配

记忆固化：L1 重要发现 → L2 语义记忆 → L3 已验证规则（模拟记忆巩固）
```

## 🔍 Trace 架构（四级）

```
L1 系统级   → span 树（工具开始/结束、耗时、mermaid）
L2 数据级   → 数据流（输入 → 输出），带 sha256 内容哈希
L3 决策级   → 结构化思维链（观察/推理/决策/备选方案）
L4 审计级   → 只追加、哈希链不可变日志（verify() 可检测篡改）
```

每条记录采用内容寻址；`replay()` 重建完整流程，`compare()` 对比不同模型的决策链差异。

## 🔮 后续规划

1. ~~LLM Provider 抽象~~ ✅（mock/openai/anthropic，可通过 `.env` 配置）
2. ~~实现 Neural Cleanse 与 Activation Clustering 真实算法~~ ✅
3. 引入 Redis 任务队列（Celery）支持异步工作流
4. ~~将哈希向量器替换为真实嵌入服务~~ ✅（可插拔 `openai` provider + 哈希回退）
5. ~~基于持久化 Trace 存储新增 `/replay/{trace_id}` 端点~~ ✅
6. ~~增加认证与限流~~ ✅（可配置，默认关闭）
7. 集成 CI/CD Webhook

## 📄 License

MIT