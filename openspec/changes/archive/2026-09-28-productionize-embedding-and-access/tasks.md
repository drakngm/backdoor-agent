# Tasks

## 1. Embedding provider

- [x] 1.1 新增 Embedder registry 与 `hashing`（默认）实现，补单测确认默认路径行为不变
- [x] 1.2 新增 `openai` embedding provider（从配置读取），补单测（mock 客户端）通过
- [x] 1.3 provider 失败回退 hashing 并告警，补测试覆盖失败路径

## 2. 语义记忆接通

- [x] 2.1 语义记忆按配置选择 embedder，补测试：切换 provider 后检索走对应向量
- [x] 2.2 文档标注切换 provider 需重建 L2 记忆，并在脚本/说明中体现

## 3. 访问控制

- [x] 3.1 新增鉴权中间件（可配置、默认关闭），补测试：关闭放行 / 开启且无凭据拒绝
- [x] 3.2 新增限流中间件（可配置、默认关闭），补测试：超阈值返回 429
- [x] 3.3 确认 API key 等敏感信息不进入 trace/报告（更新相关测试）

## 4. 文档

- [x] 4.1 更新 `README.md` Production Path #4/#6 与配置说明，确认与实际一致
