# Command Center BFF

Backend-for-Frontend 层，为前端提供：

- 仪表盘读模型：`/dashboard/*`、`/detection/*`、`/workflow/dag/live`、`/memory/stats`、`/traces`、`/logs`、`/threats`、`/system/resources`
- 执行代理：`POST /execute/{agent|workflow|hybrid}` → 转发到核心 FastAPI（仓库根 `app/`），失败时降级为仿真数据

## 运行

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```

## 与核心后端对接

默认向 `http://localhost:8000` 转发。可通过 `CORE_API_URL` 覆盖，或设为空字符串以强制使用 mock。