# 制造领航 ForgePilot

> 面向中小制造企业的设备知识、故障诊断与维护协同 AI Agent。

ForgePilot 希望把设备台账、说明书、维修记录、点检数据和备件信息连接起来，让一线人员可以用自然语言查询设备知识、获得有证据的诊断建议，并把结果转化为可追踪的维护任务。

本项目面向 Web 网站开发比赛的 **AI Agent智能助手** 与 **RAG知识问答系统** 方向，也是一个围绕数据库、工业业务流程和AI工程构建的工业软件作品集项目。

## 当前状态

当前仓库处于早期后端原型阶段。

已实现：

- FastAPI应用骨架与健康检查接口；
- 说明书RAG知识库：文档入库、BM25检索、带页码/分块证据引用；
- 真实模型适配器：OpenAI兼容接口、JSON结构化输出、Pydantic校验；
- 诊断接口：区分事实/推断/待确认，过滤非法引用，处理无答案与模型不可用；
- 设备事实提供方抽象：`static`离线演示与`http`调用B包设备接口；
- 设备不存在、无知识、型号不匹配、设备服务不可用等降级状态；
- 提示注入防护、客户端复用、连续调用与降级测试；
- C 侧组织隔离：文档按 `organization_id` 隔离，`/chat`、`/search`、`/documents` 需要组织上下文；
- 默认关闭文档入库写接口，生产环境禁止 `static` 设备提供方与 Mock 模型；
- CORS、请求体上限、按 IP 限流、请求 ID 与可关闭的 OpenAPI 文档；
- 设备事实、引用来源、冲突来源均做校验，模型返回非法 JSON 时明确降级；
- 3 份虚构演示手册与 20 条评测集；
- 83 项自动化测试；
- 已用 B 侧 SQLite 种子数据完成 AC-07 真实设备事实联调（模型仍为 Mock，真实模型待密钥复测）。

尚未实现：

- Web前端；
- PostgreSQL设备数据库（本仓库C侧不落库）；
- Agent工具调用与工单闭环；
- 备件、权限、审计和生产部署。

完整方案、分工和里程碑见 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)。AC-07 的 C↔B 联调记录见 [docs/integration-ac07.md](docs/integration-ac07.md)。参与开发前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 本地运行

需要 Python 3.10 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开：

- API文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

运行测试和代码检查：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

导入演示文档并运行检索评测：

```powershell
.\.venv\Scripts\python.exe -m scripts.ingest_demo
.\.venv\Scripts\python.exe -m scripts.evaluate
```

### 模型配置（可选）

默认使用 `MockLLM`（`is_mock=true`）。接入真实模型时设置环境变量：

```powershell
$env:LLM_PROVIDER = "openai"
$env:LLM_API_KEY  = "你的密钥"
$env:LLM_BASE_URL = "https://api.example.com/v1"
$env:LLM_MODEL    = "模型名"
$env:LLM_MAX_TOKENS = "1024"
```

密钥只放后端环境变量，不提交到仓库。真实调用成功才 `is_mock=false`；未配置或调用失败时降级为返回检索证据（`status=model_unavailable`），不伪造结论。`APP_ENV=production` 时禁止 `LLM_PROVIDER=mock`。

### 设备事实配置（可选）

默认 `DEVICE_PROVIDER=static`，使用内置演示设备，仅用于离线运行和测试。接入B包真实设备接口时：

```powershell
$env:DEVICE_PROVIDER = "http"
$env:DEVICE_API_BASE_URL = "http://127.0.0.1:8001"
$env:DEVICE_API_TIMEOUT = "5"
```

- C 不再从环境变量固定组织、用户或 token；每次 `/chat` 请求的
  `Authorization: Bearer`、`X-Organization-Id`、`X-User-Id` 会原样透传给 B。
- C 侧接口默认要求 `X-Organization-Id`（`C_REQUIRE_AUTH=true`）；生产环境应由网关注入，不能由浏览器任意选择组织。
- 调用 `GET /api/v1/devices/{device_id}`，使用 `state` 作为设备状态、`model` 作为型号。
- 设备不存在返回 `device_not_found`，跨组织或越权返回 `device_unauthorized`，超时/5xx 返回 `device_unavailable`。
- B 返回的设备编号与请求不一致时返回 `device_mismatch`，拒绝使用该设备事实。
- 响应中的 `device_source`（`static`/`http`）和 `is_demo` 会明确标记设备事实与模型是否为演示模式。
- 设备型号到知识库文档域的默认映射为 `GX11→compressor-002`、`P-102X→pump-004`、`GMC-4000→cnc-003`，可用 `DEVICE_KNOWLEDGE_MODELS` JSON 覆盖。
- 生产环境必须使用 `http`；`APP_ENV=production` 时启动会拒绝 `static`。

## 当前接口

| 方法 | 路径 | 状态 | 用途 |
|---|---|---|---|
| GET | `/health` | 已实现 | 服务健康检查与当前 provider 模式 |
| POST | `/api/v1/chat` | 已实现 | 接收设备ID和问题，返回带证据的诊断结果 |
| POST | `/api/v1/search` | 已实现 | 检索当前组织文档，返回带页码的证据 |
| POST | `/api/v1/documents/ingest` | 受控 | 文档入库，默认关闭（`C_ENABLE_INGEST=false`） |
| GET | `/api/v1/documents` | 已实现 | 列出当前组织文档，支持 `limit/offset` |

除 `/health` 外，接口需要 `X-Organization-Id`；生产环境建议由网关注入，并同时透传 Bearer token。

### 诊断状态与 HTTP 状态

`status` 取值：`ok`、`no_answer`、`model_unavailable`、`device_not_found`、
`device_unauthorized`、`device_unavailable`、`device_mismatch`、`no_knowledge`、
`model_mismatch`。

- `device_not_found` → HTTP 404
- `device_unauthorized` → HTTP 403
- `device_mismatch` → HTTP 502
- `device_unavailable` → HTTP 503
- 其余诊断结果返回 HTTP 200，客户端必须检查 `status`

响应中的 `device_source` 和 `is_demo` 用于区分真实设备/模型与演示数据；只有
`status=ok` 且 `is_demo=false` 才能视为真实诊断成功。

### 安全配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | `production` 时禁止 Mock 模型与 static 设备 |
| `C_REQUIRE_AUTH` | `true` | 是否要求 `X-Organization-Id` |
| `C_DEFAULT_ORGANIZATION_ID` | `demo-org` | 关闭鉴权时的演示组织 |
| `C_ENABLE_INGEST` | `false` | 是否开放文档写接口 |
| `CORS_ORIGINS` | 本地 Vite 地址 | 允许的前端来源，逗号分隔 |
| `RATE_LIMIT_PER_MINUTE` | `60` | 每 IP 每分钟请求上限；`0` 为关闭 |
| `MAX_REQUEST_BYTES` | `1000000` | 请求体上限 |
| `DOCS_ENABLED` | `true` | 是否开放 `/docs` 和 OpenAPI |
| `LLM_MAX_TOKENS` | `1024` | 模型输出上限 |
| `HTTP_TRUST_ENV` | `false` | 是否读取系统代理环境变量 |

## 已知限制

- 本仓库只包含C侧检索诊断服务，不包含前端、数据库写入和工单流程。
- 默认BM25检索，尚未接入向量检索；适用于小型演示知识库。
- `static`设备提供方只用于离线演示，生产必须配置`http`；生产启动会拒绝 static。
- 真实模型需要兼容OpenAI的`/chat/completions`与JSON模式；不支持时返回`model_unavailable`。
- 设备型号到知识库文档域仍需受控映射，待B包直接返回`knowledgeModel`后可移除。
- 知识库目前是进程内 JSON + 单机锁；多 worker 部署会出现各自内存与文件竞争，正式环境应迁移 PostgreSQL/pgvector。
- 限流是单进程内存实现，多 worker 或网关部署时应在网关层统一限流。
- `MAX_REQUEST_BYTES` 依赖 `Content-Length`；生产网关还应限制 chunked/无长度请求体。
- C 侧组织隔离依赖请求头 `X-Organization-Id`；生产必须由可信网关注入，不能直接信任公网浏览器提交的值。
- 回退方式：将`LLM_PROVIDER`和`DEVICE_PROVIDER`恢复为`mock`/`static`，并设置 `C_REQUIRE_AUTH=false`、`C_ENABLE_INGEST=true` 回到无外部依赖的本地演示模式（仅限开发）。

## 目标业务闭环

```text
选择设备 / 扫码进入设备档案
  → 查询说明书、维修记录和实时/导入数据
  → Agent判断需要调用的工具
  → RAG给出带来源的分析
  → 生成检查步骤与风险提示
  → 人工确认
  → 创建维护工单并关联备件
  → 记录处理结果，沉淀为企业知识
```

## 协作方式

项目采用：

```text
Issue → feature/fix分支 → Pull Request → 同伴审查 → Squash合并
```

不要直接向 `main` 提交业务代码。每个分支只解决一个Issue，PR中必须说明改动原因、测试结果、接口或数据库变化。详细规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 安全说明

- 禁止提交API Key、密码和私钥；
- 禁止上传未经授权的企业说明书、设备数据和维修记录；
- 演示材料必须使用虚构或脱敏数据；
- 文档入库默认关闭，生产环境不得开放无鉴权写接口；
- 组织上下文必须由可信网关注入，C 侧不能信任公网浏览器任意提交的 `X-Organization-Id`；
- AI建议不能替代安全规范、专业维修判断和人工确认；
- 高风险操作必须提示停机、断电和现场安全要求。

## License

[MIT](LICENSE)

