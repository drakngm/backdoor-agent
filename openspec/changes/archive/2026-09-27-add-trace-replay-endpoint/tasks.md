# Tasks

## 1. 持久化存储层

- [x] 1.1 在 `app/trace/` 新增 trace 持久化存储（写/读/存在性判断），并对其进行单元测试（写入后可按 id 读回）通过
- [x] 1.2 在持久化前过滤敏感字段，并补测试断言凭据不出现在落盘内容中

## 2. 执行后落盘

- [x] 2.1 在 `Dispatcher` 执行结束处持久化四级 trace，补测试：三种模式执行后均可在存储中找到对应 trace_id
- [x] 2.2 验证 Windows 路径与 `BACKDOOR_DATA_DIR` 配置生效（测试或脚本运行确认）

## 3. 回放端点

- [x] 3.1 新增 `GET /replay/{trace_id}` 路由并在 `app/api/router.py` 聚合，补端点测试：已知 id 返回含 timeline/decisions/data_flow/audit 的响应
- [x] 3.2 补未命中测试：未知 id 返回 404 与结构化错误
- [x] 3.3 更新 `README.md` 端点表与 Production Path #5 状态，确认文档与实现一致
