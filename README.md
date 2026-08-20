# 🔒 AI Backdoor Detection & Defense Agent System

> **Hybrid AI agent for automated backdoor detection in deep learning models.**

Combines an **Agent Loop** (high-level reasoning & detection strategy decisions) with a
**DAG Workflow** (deterministic tool orchestration), a **unified tool contract**, a
**3-layer hierarchical memory**, and a **four-level trace system** for full
interpretability & auditability.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI ENTRY LAYER                        │
│    /health   /run_agent   /run_workflow   /run_hybrid        │
└───────────────┬──────────────┬──────────────┬────────────────┘
                │              │              │
      ┌─────────▼────┐  ┌──────▼──────┐  ┌────▼─────────────┐
      │  Agent Mode   │  │ Workflow Mode│  │  Hybrid Mode     │
      │  agent_loop   │  │ planner + DAG│  │  decision engine │
      │  tool_router  │  │ executor     │  │  -> DAG compiler │
      │  hooks        │  │ strategies   │  │  -> executor     │
      └───────┬───────┘  └──────┬───────┘  └────────┬────────┘
              │                 │                   │
              └────────────┬────┴───────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │         Shared Tool Layer             │
        │  ToolContract / ToolAdapter / Artifact │
        │  ToolRegistry + Mock/Real detectors    │
        └──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────────┐
        ▼                  ▼                       ▼
   LLM Provider      Hierarchical Memory      Four-Level Trace
   (mock/openai/     (episodic/semantic/      (system/data/decision
    anthropic)        procedural + 固化)        /audit + CoT + replay)
```

## 🔑 Key Features

- **Hybrid Agent Architecture**: Agent Loop (LLM/rule-driven reasoning) + DAG Workflow
  (deterministic execution). The agent decides tool selection & order based on model
  metadata and intermediate results; each decision compiles into a DAG node.
- **Three Execution Modes**: Agent (`/run_agent`), Workflow (`/run_workflow`), Hybrid (`/run_hybrid`)
- **LLM Provider Abstraction**: `LLMClient` interface with mock / OpenAI / Anthropic
  implementations (OpenAI-compatible endpoints like DeepSeek work out of the box via `.env`)
- **Unified Tool Contract**: `ToolContract` (manifest) + `ToolAdapter` (Adapter pattern) +
  standardized `Artifact` model — new detectors plug in by implementing one interface
- **Pre/Post Hook Validation**: decision-based hooks (`allow`/`deny`) for input validation
  (PreToolUse) and result verification (PostToolUse)
- **3-Layer Hierarchical Memory**: Episodic (Redis sliding window) → Semantic (vector) →
  Procedural (rules), with a memory-consolidation (固化) mechanism
- **Four-Level Trace**: System spans → Data flow (hashed) → Decision CoT → immutable Audit
  trail (hash-chained), with replay + cross-trace comparison
- **Standardized Safety Outputs**: `confidence_score`, `risk_level` (LOW/MEDIUM/HIGH), artifacts

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) configure LLM provider in .env
#   BACKDOOR_LLM_PROVIDER=openai
#   BACKDOOR_LLM_API_BASE_URL=https://opencode.ai/zen/go/v1
#   BACKDOOR_LLM_API_KEY=sk-...
#   BACKDOOR_LLM_MODEL=deepseek-v4-flash

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
| `POST` | `/run_hybrid` | Hybrid Mode: Agent decisions → DAG → report |

### Example: Hybrid Mode (Agent decision + DAG execution)

```bash
curl -X POST http://localhost:8000/run_hybrid \
  -H "Content-Type: application/json" \
  -d '{"message": "检测一个 ResNet-18 模型中是否存在后门", "model_path": "resnet18.h5"}'
```

Response includes:
- `verdict` / `confidence` / `final_answer`: final detection conclusion
- `decisions`: the agent's decision chain (tool + params + `depends_on`)
- `tool_results`: standardized tool outputs (risk level, confidence, is_backdoor)
- `trace`: four-level trace replay — `decisions` (CoT), `data_flow` (hashed), `audit`
- `memory_consolidation`: L1→L2→L3 consolidation counts
- `mermaid`: execution flow visualization

## 📁 Project Structure

```
backdoor-agent/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── entry/dispatcher.py      # agent / workflow / hybrid mode dispatch
│   ├── api/                     # REST endpoints (health, agent, workflow, hybrid)
│   ├── agents/                  # Agent Runtime (agent_loop, tool_router, hooks)
│   ├── hybrid/                  # Hybrid Agent (model_analyzer, decision_engine, compiler)
│   ├── llm/                     # LLM Provider abstraction (base, registry, mock/openai/anthropic)
│   ├── workflow/                # Workflow Engine (planner, task_graph, executor)
│   │   └── strategies/          # Scan strategies (fast/deep/forensic)
│   ├── tools/                   # Tool layer (contract, base, adapter, registry, mocks)
│   ├── memory/                  # Hierarchical memory (episodic/semantic/procedural + consolidation)
│   ├── trace/                   # Four-level trace (models, audit, trace, hooks)
│   ├── core/                    # Global infra (config, execution_trace, exceptions, logging)
│   ├── security/                # Detection algorithm implementations
│   └── report/                  # Report generator
├── configs/                     # YAML + Python settings (pydantic-settings)
├── tests/                       # pytest test suite
├── docker/                      # Docker & docker-compose (interface reserved)
├── scripts/                     # Dev scripts (run_dev, init_redis)
├── PRD.md                       # Product requirements & milestone status
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
- **Redis** — L1 episodic memory (optional, falls back to in-memory)
- **Hashing embedder** — dependency-free text vectors (pluggable for `text-embedding-3-small`)
- **Docker** — interface reserved (not implemented this phase)

## 🔒 Detection Tools

| Tool | Description | Status |
|------|-------------|--------|
| `strip_detect` | STRIP: entropy-based perturbation detection | Mock (random) |
| `neural_cleanse` | Neural Cleanse: trigger reverse-engineering + MAD | Mock |
| `activation_clustering` | Activation Clustering: PCA/t-SNE + K-Means | Mock |
| `strip_detect_real` | Real STRIP algorithm (pure Python, injectable predictor) | Real |

## 📊 Scan Strategies

| Strategy | Tools | Duration | Use Case |
|----------|-------|----------|----------|
| `fast_scan` | STRIP only | ~30s | CI/CD pipeline gate |
| `deep_scan` | STRIP + NC + AC (parallel) | ~5min | Pre-release model audit |
| `forensic_scan` | All detectors | ~30min | Incident response investigation |

## 🧠 Memory Architecture

```
L1 Episodic (短期)   →  Redis sliding window (N=20), keyword match, session-scoped
L2 Semantic (中期)   →  vectorized findings (hashing embedder), semantic search,
                        cross-session persistent (JSON)
L3 Procedural (长期) →  structured rules + vectorized case base, strategy matching

Memory Consolidation: L1 重要发现 → L2 语义记忆 → L3 已验证规则 (模拟记忆巩固)
```

## 🔍 Trace Architecture (Four Levels)

```
L1 System   → span tree (tool start/end, durations, mermaid)
L2 Data     → data flow (input → output) with sha256 content hashes
L3 Decision → structured Chain-of-Thought (observation/reasoning/decision/alternatives)
L4 Audit    → append-only, hash-chained immutable log (verify() detects tampering)
```

Every record is content-addressed; `replay()` reconstructs the full flow, and
`compare()` diffs decision chains across models.

## 🔮 Production Path

1. ~~LLM Provider abstraction~~ ✅ (mock/openai/anthropic, configurable via `.env`)
2. Implement Neural Cleanse & Activation Clustering real algorithms (STRIP done)
3. Add Redis-backed task queues (Celery) for async workflows
4. Replace hashing embedder with a real embedding service (e.g. `text-embedding-3-small`)
5. Add `/replay/{trace_id}` endpoint backed by persisted trace storage
6. Add authentication + rate limiting
7. Integrate CI/CD webhooks

## 📄 License

MIT
