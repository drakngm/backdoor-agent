# AI Backdoor Detection · Command Center (Web)

前后端分离的前端工作台与 BFF 层，作为 `AI Backdoor Detection & Defense Agent System`
（仓库根目录 `app/`，FastAPI）的可视化指挥中心。

```
web/
├── frontend/   # React 18 + TypeScript + Vite + Tailwind CSS v4 前端
└── backend/    # FastAPI BFF：仪表盘读模型 + 执行代理（核心后端不可用时自动降级 mock）
```

## 启动前端

```bash
cd web/frontend
npm install
npm run dev          # http://localhost:5173
```

Vite 已在 `vite.config.ts` 将 `/api` 代理到 `http://localhost:8001`（BFF）。

生产构建：

```bash
npm run build
npm run preview
```

## 启动 BFF（可选）

```bash
cd web/backend
python -m pip install -r requirements.txt
uvicorn app.main:app --port 8001
```

环境变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `BFF_PORT` | `8001` | BFF 监听端口 |
| `CORE_API_URL` | `http://localhost:8000` | 核心 FastAPI 地址 |
| `ALLOW_MOCK_FALLBACK` | `true` | 核心后端不可用时是否返回仿真数据 |

前端 API 客户端（`frontend/src/api/client.ts`）在 BFF 不可用时会自动降级为
本地 mock 数据（`frontend/src/api/mock.ts`），因此即使不启动任何后端，界面仍可完整演示。