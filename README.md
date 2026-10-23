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
- 3 份虚构演示手册与 20 条评测集；
- 63 项自动化测试；
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
```

密钥只放后端环境变量，不提交到仓库。真实调用成功才 `is_mock=false`；未配置或调用失败时降级为返回检索证据（`status=model_unavailable`），不伪造结论。

### 设备事实配置（可选）

默认 `DEVICE_PROVIDER=static`，使用内置演示设备，仅用于离线运行和测试。接入B包真实设备接口时：

```powershell
$env:DEVICE_PROVIDER = "http"
$env:DEVICE_API_BASE_URL = "http://127.0.0.1:8001"
$env:DEVICE_API_TIMEOUT = "5"
```

- C 不再从环境变量固定组织、用户或 token；每次 `/chat` 请求的
  `Authorization: Bearer`、`X-Organization-Id`、`X-User-Id` 会原样透传给 B。
- 调用 `GET /api/v1/devices/{device_id}`，使用 `state` 作为设备状态、`model` 作为型号。
- 设备不存在返回 `device_not_found`，跨组织或越权返回 `device_unauthorized`，超时/5xx返回 `device_unavailable`。
- B 返回的设备编号与请求不一致时返回 `device_mismatch`，拒绝使用该设备事实。
- 设备型号到知识库文档域的默认映射为 `GX11→compressor-002`、`P-102X→pump-004`、`GMC-4000→cnc-003`，可用 `DEVICE_KNOWLEDGE_MODELS` JSON 覆盖。
- 生产环境必须使用 `http`；`static` 不得作为真实设备事实来源。

## 当前接口

| 方法 | 路径 | 状态 | 用途 |
|---|---|---|---|
| GET | `/health` | 已实现 | 服务健康检查 |
| POST | `/api/v1/chat` | 已实现 | 接收设备ID和问题，返回带证据的诊断结果 |
| POST | `/api/v1/search` | 已实现 | 检索文档，返回带页码的证据 |
| POST | `/api/v1/documents/ingest` | 已实现 | 文档入库 |
| GET | `/api/v1/documents` | 已实现 | 列出已入库文档 |

### 诊断状态

`status` 取值：`ok`、`no_answer`、`model_unavailable`、`device_not_found`、
`device_unauthorized`、`device_unavailable`、`device_mismatch`、`no_knowledge`、
`model_mismatch`。

只有 `ok` 表示模型返回了可核实的结构化诊断；其余状态均不得当作成功结果展示。

## 已知限制

- 本仓库只包含C侧检索诊断服务，不包含前端、数据库写入和工单流程。
- 默认BM25检索，尚未接入向量检索；适用于小型演示知识库。
- `static`设备提供方只用于离线演示，生产必须配置`http`。
- 真实模型需要兼容OpenAI的`/chat/completions`与JSON模式；不支持时返回`model_unavailable`。
- 设备型号到知识库文档域仍需受控映射，待B包直接返回`knowledgeModel`后可移除。
- 回退方式：将`LLM_PROVIDER`和`DEVICE_PROVIDER`恢复为`mock`/`static`即可回到无外部依赖的演示模式。

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
- AI建议不能替代安全规范、专业维修判断和人工确认；
- 高风险操作必须提示停机、断电和现场安全要求。

## License

[MIT](LICENSE)

