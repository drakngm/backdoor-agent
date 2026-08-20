# 🔒 AI Backdoor Detection & Defense Agent System

> **Production-grade AI agent for automated backdoor detection in deep learning models.**

Built on a **3-layer architecture**:
1. **Workflow Layer** (DeerFlow-style Planner + DAG execution)
2. **Agent Runtime Layer** (Claude Code Harness-style LLM→Tool→Observe→Loop)
3. **Shared Tool Layer** (Unified contract-based tool system with 4 detection algorithms)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────┐
│              FastAPI ENTRY LAYER             │
│  /health   /run_agent   /run_workflow        │
└──────────────┬──────────────┬────────────────┘
               │              │
      ┌────────▼────┐   ┌─────▼──────────┐
      │ Agent Mode   │   │ Workflow Mode   │
      │ agent_loop   │   │ planner + DAG  │
      │ tool_router  │   │ executor       │
      │ hooks        │   │ strategies     │
      └──────┬───────┘   └──────┬─────────┘
             │                  │
             └────────┬─────────┘
                      ▼
           ┌───────────────────┐
           │  Shared Tool Layer │
           │  ToolContract      │
           │  ToolRegistry      │
           │  Mock Tools (×3)   │
           └───────────────────┘
```

## 🔑 Key Features

- **Dual Execution Modes**: Interactive Agent (LLM-driven) + Batch Workflow (DAG-driven)
- **4-Layer Memory System**: Working → Session → Project → Knowledge (RAG)
- **ToolContract Standard**: Every tool has validated input/output schemas, timeout, GPU requirements
- **Execution Trace Graph**: Full span-tree tracing with Mermaid visualization
- **Hook System**: BeforeTool/AfterTool/OnError lifecycle hooks
- **Multi-Strategy Planner**: fast_scan / deep_scan / forensic_scan
- **Standardized Safety Outputs**: confidence_score, risk_level (LOW/MEDIUM/HIGH), artifact tracking

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
python scripts/run_dev.py
```

API available at `http://localhost:8000/docs`

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | System health + registered tools + strategies |
| `POST` | `/run_agent` | Agent Mode: LLM → Tool → Observation Loop |
| `POST` | `/run_workflow` | Workflow Mode: Planner → DAG → Parallel Exec |

### Example: Agent Mode

```bash
curl -X POST http://localhost:8000/run_agent \
  -H "Content-Type: application/json" \
  -d '{"message": "Detect backdoors in model.h5"}'
```

Response includes:
- `trace_id`: Unique correlation ID
- `spans`: Complete execution chain (LLM calls + tool executions)
- `mermaid`: Visual flowchart of the execution
- `critical_path`: Longest-duration execution path

### Example: Workflow Mode

```bash
curl -X POST http://localhost:8000/run_workflow \
  -H "Content-Type: application/json" \
  -d '{"strategy": "deep_scan", "model_path": "model.h5"}'
```

## 📁 Project Structure

```
backdoor-agent/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── entry/dispatcher.py      # Agent/Workflow mode dispatch
│   ├── api/                     # REST endpoints (health, agent, workflow)
│   ├── agents/                  # Agent Runtime (agent_loop, tool_router, hooks)
│   ├── workflow/                # Workflow Engine (planner, task_graph, executor)
│   │   └── strategies/          # Scan strategies (fast/deep/forensic)
│   ├── tools/                   # Shared Tool Layer (contract, base, registry, mocks)
│   ├── memory/                  # 4-Layer Memory (working, session, project, knowledge)
│   ├── core/                    # Global infrastructure (config, trace, exceptions, logging)
│   ├── security/                # Reserved: algorithm implementations
│   └── report/                  # Report generator
├── configs/                     # YAML + Python settings (pydantic-settings)
├── tests/                       # pytest test suite
├── docker/                      # Docker & docker-compose
├── scripts/                     # Dev scripts (run_dev, init_redis)
└── README.md
```

## 🧪 Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v --asyncio-mode=auto
```

## 🛠 Technology Stack

- **Python 3.10+**
- **FastAPI** — async REST API
- **Pydantic v2** — schema validation
- **asyncio** — concurrent execution
- **YAML** — configuration
- **Redis** — reserved for task queues (optional)
- **Docker** — deployment

## 🔒 Security Tools (Mock Implementations)

| Tool | Description | Tags |
|------|-------------|------|
| `strip_detect` | STRIP: Entropy-based perturbation detection | detection, gpu, fast_scan |
| `neural_cleanse` | Neural Cleanse: Trigger reverse-engineering + MAD | detection, gpu, deep_scan |
| `activation_clustering` | Activation Clustering: PCA/t-SNE + K-Means | detection, gpu, deep_scan |

## 📊 Scan Strategies

| Strategy | Tools | Duration | Use Case |
|----------|-------|----------|----------|
| `fast_scan` | STRIP only | ~30s | CI/CD pipeline gate |
| `deep_scan` | STRIP + NC + AC (parallel) | ~5min | Pre-release model audit |
| `forensic_scan` | All detectors | ~30min | Incident response investigation |

## 🧠 Memory Architecture

```
Working Memory (L1)  →  Current LLM reasoning window (~8K tokens)
Session Memory (L2)  →  Full task conversation history
Project Memory (L3)  →  Persistent reports + model fingerprints
Knowledge Memory(L4) →  RAG: Security knowledge base (publications, best practices)
```

All layers follow a degrade strategy: L1→L2→L3→L4 fallback on cache miss.

## 🔮 Production Path

1. Replace Mock LLM with real API (OpenAI/Anthropic)
2. Implement real detection algorithms in `app/security/`
3. Add Redis/Celery for async task queues
4. Replace Project Memory JSON with SQLite/PostgreSQL
5. Add vector DB (ChromaDB/Pinecone) for Knowledge Memory
6. Add authentication + rate limiting
7. Integrate CI/CD webhooks

## 📄 License

MIT