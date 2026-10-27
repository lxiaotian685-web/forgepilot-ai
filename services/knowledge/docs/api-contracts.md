# 诊断与确认建单 API 契约（v1.3，已对齐 B 实现）

> 状态：C 侧契约，已对齐 B 的 `docs/api-contracts/business-api.yaml`（PR #16 实际实现）。
> 关联：Issue #12（C 有据诊断）、Issue #11（B 诊断持久化）、Issue #4（端到端闭环）。
> v1.3：C 侧新增组织隔离、鉴权要求、写接口开关、限流与 HTTP 状态映射。

## 1. 角色与边界

| 角色 | 职责 | 边界 |
|---|---|---|
| C | 检索、模型调用、返回证据 | 默认只读；文档写入默认关闭 |
| B | 设备事实、权限、诊断落库、确认建单、审计 | 写路径唯一入口 |
| A | 交互、页面反馈 | 不提交 `equipment_model` |

- 权威设备事实和型号来自 B 的设备查询；C 不再用静态表维护设备事实。
- `static` 提供方只用于离线演示与测试，生产必须配置 `DEVICE_PROVIDER=http`；`APP_ENV=production` 时 static 会启动失败。
- 设备型号到知识库文档域的映射是 C 的临时兼容字段，待 B 返回 `knowledgeModel` 后移除。
- 模型（C）不能直接建单，必须走 B 的确认接口。
- 组织与用户来自认证上下文，前端不在请求体传 `organization_id`。

## 2. 认证与权限

- 组织与用户来自**认证上下文**，不在 JSON 请求体。
- B 演示模式：请求头 `X-Organization-Id`、`X-User-Id`；缺省回落到 demo 组织/用户。
- B 生产模式：`Authorization: Bearer <token>`（token 内含 org/user，HMAC 签名）。
- C 默认要求 `X-Organization-Id`（`C_REQUIRE_AUTH=true`），用于知识库组织隔离；C 不自行签发 token，生产应由可信网关注入组织上下文。
- 角色等级：`viewer < technician < manager < admin < owner`。
- 跨组织资源一律返回 404。

## 3. C 侧接口

### 3.1 诊断 `POST /api/v1/chat`

请求 `{device_id, question, equipment_model?}`；响应 `{device_id, answer, summary, statements, sources, conflicts, verification_suggestions, is_mock, device_source, is_demo, status}`。

`device_source` 为 `static`/`http`，`is_demo` 表示模型或设备事实至少一方为演示模式；只有 `status=ok` 且 `is_demo=false` 才表示真实诊断成功。

`status`：

- `ok`：模型返回了可核实引用的结构化诊断；
- `no_answer`：检索无证据，或事实引用全部无法核实；
- `model_unavailable`：模型未配置、超时、限流或返回格式异常，降级返回检索证据；
- `device_not_found`：B 返回 404 或设备不存在；
- `device_unauthorized`：B 返回 401/403，不泄漏跨组织设备存在性；
- `device_unavailable`：B 超时、5xx 或响应无法解析；
- `device_mismatch`：B 返回的设备编号与请求的 `device_id` 不一致；
- `no_knowledge`：设备存在但无可用的知识库文档域；
- `model_mismatch`：传入的 `equipment_model` 与设备事实不一致。

只有 `ok` 表示成功；其他状态不得作为诊断成功展示。

HTTP 状态映射：

| `status` | HTTP |
|---|---|
| `device_not_found` | 404 |
| `device_unauthorized` | 403 |
| `device_mismatch` | 502 |
| `device_unavailable` | 503 |
| 其他诊断状态 | 200（客户端必须检查 `status`） |

### 3.2 检索与文档

- `POST /api/v1/search`：检索当前组织文档，需要 `X-Organization-Id`。
- `GET /api/v1/documents`：列出当前组织文档，支持 `limit`（1–500）和 `offset`。
- `GET /api/v1/documents/{document_id}`：读取当前组织文档及解析切片，供上传后核对；原始 PDF 字节未保存，不提供原文件下载。
- `DELETE /api/v1/documents/{document_id}`：管理岗位及以上删除文档和所有切片；跨组织对象返回 404。
- `POST /api/v1/documents/upload`：上传 PDF/TXT/MD，解析后入库；管理岗位及以上可用，默认关闭（`C_ENABLE_INGEST=false`）。
- `POST /api/v1/documents/ingest`：文本内容入库；与上传接口使用同一岗位校验，默认关闭（`C_ENABLE_INGEST=false`）。

### 3.2.1 文档上传 `POST /api/v1/documents/upload`

`Content-Type: multipart/form-data`

| 字段 | 必填 | 说明 |
|---|---|---|
| `file` | 是 | PDF、TXT 或 MD，单文件大小受 `MAX_UPLOAD_BYTES` 限制 |
| `title` | 否 | 缺省使用文件名（不含扩展名） |
| `equipment_model` | 是 | 知识域，例如 `compressor-002` |
| `version` | 否 | 默认 `1.0`，最长 50 |
| `source` | 否 | 缺省使用文件名，最长 500 |

响应：

```json
{
  "document_id": "a1b2c3d4",
  "title": "空压机维修规范",
  "equipment_model": "compressor-002",
  "version": "1.0",
  "source": "manual.pdf",
  "page_count": 4,
  "chunk_count": 9
}
```

错误：

- 403：`C_ENABLE_INGEST=false`
- 413：文件或请求体超过上限
- 415：扩展名不支持，或 PDF 文件头不合法
- 422：缺少字段、空白字段、文件为空、PDF 损坏/无可提取文本、文本编码无法识别
- 401：`C_REQUIRE_AUTH=true` 且缺少 `X-Organization-Id`

组织编号只从请求上下文获取，不能由表单或文件内容指定。PDF 仅支持可提取文本，扫描件需要 OCR，当前不处理。

### 3.3 设备事实接入（C 已实现）

C 在检索前调用 B 的 `GET /api/v1/devices/{device_id}`，字段映射：

| C 内部字段 | B 响应字段 | 说明 |
|---|---|---|
| `device_id` | `id` | 设备编号 |
| `name` | `name` | 设备名称 |
| `type` | `type` | 设备类别 |
| `model` | `model` | 设备型号 |
| `location` | `location` | 位置 |
| `status` | `state` | B 使用 `state`，C 将 `需关注/告警/运行/停机/维护` 归一化为 `attention/alert/running/stopped/maintenance` |
| `organization_id` | 认证上下文 | 不在响应体 |

知识域解析顺序：

1. B 响应中的 `knowledgeModel`（若提供）；
2. `DEVICE_KNOWLEDGE_MODELS` 环境变量；
3. 默认映射 `GX11→compressor-002`、`P-102X→pump-004`、`GMC-4000→cnc-003`；
4. 仍无法解析时返回 `no_knowledge`，不得猜测文档。

环境变量只保留连接配置：

```text
APP_ENV=development|production
DEVICE_PROVIDER=static|http
DEVICE_API_BASE_URL
DEVICE_API_TIMEOUT=5
DEVICE_KNOWLEDGE_MODELS={"GX11":"compressor-002"}
C_REQUIRE_AUTH=true
C_DEFAULT_ORGANIZATION_ID=demo-org
C_ENABLE_INGEST=false
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
RATE_LIMIT_PER_MINUTE=60
MAX_REQUEST_BYTES=6000000
MAX_UPLOAD_BYTES=5000000
DOCS_ENABLED=true
LLM_MAX_TOKENS=1024
HTTP_TRUST_ENV=false
```

C **不得**从环境变量固定组织、用户或 token。每次 `/chat` 请求的
`Authorization: Bearer <token>`、`X-Organization-Id`、`X-User-Id` 会原样透传给 B；
演示模式使用后两者，生产模式使用 Bearer。跨组织一律返回 404，C 转换为
`device_not_found`；B 返回的设备编号与请求不一致时，C 返回 `device_mismatch`
并拒绝使用该设备事实。

## 4. C 侧证据引用扩展（已实现）

> 稳定引用 ID、`source_ids`、`conflicts` 与 `verification_suggestions` 已落地；真实模型输出经 Pydantic 校验，非法引用不会伪装成成功。

### 4.1 稳定引用 ID（含分块维度）

每条 `source` 增加稳定、可回查字段：

```json
{
  "id": "a1b2c3d4@v1.0#p2c0",
  "document_id": "a1b2c3d4",
  "version": "1.0",
  "page": 2,
  "chunk_index": 0,
  "title": "空压机维修规范",
  "snippet": "……",
  "score": 0.946
}
```

- `id = "{document_id}@{version}#p{page}c{chunk_index}"`，分块维度保证同页多分块不重复。
- `page` 允许 `null`，未知页码标 `null`，不得编造。

### 4.2 `statement.source_ids`

每条 `statement` 增加 `source_ids`，指向本次返回 `sources` 的稳定 ID；模型引用不在本次 `sources` 中视为错误引用。

只要存在任何一条事实无法关联到本次 `sources`（包括混合有效/无效引用），整体返回 `no_answer`，替换模型原回答，不保留无依据事实的叙述；有效事实仍保留，无效事实降级为 `pending`。`statement.source` 由 C 根据有效 `source_ids` 重新生成，不采用模型自填的来源文本。

### 4.3 `conflicts` 与 `verification_suggestions`

- `conflicts`：设备事实与文档结论不一致时，同时展示双方来源，禁止静默覆盖。
- `origin=document` 且 `ref` 不在本次 `sources` 中的冲突来源会被丢弃；全部来源被丢弃时整条冲突丢弃。
- `verification_suggestions`：说明缺什么证据、用于核验什么判断。
- 禁止编造置信度、概率变化或自动修改设备参数。

## 5. 诊断保存与查询（B，已实现）

C 的 `/api/v1/chat` 返回结果后，由 B 保存；字段映射：

| chat 响应 | diagnosis |
|---|---|
| `device_id` | `deviceId` |
| `question` | `question` |
| `answer` | `conclusion` |
| `sources` / `statements` | `evidence`（快照）|
| 模型来源 / `is_mock` | `modelSource` |

### 5.1 保存 `POST /api/v1/diagnoses`（201）

请求 `DiagnosisCreate`：

```json
{
  "deviceId": "AC-07",
  "question": "AC-07 振动突然升高，可能是什么原因？",
  "conclusion": "疑似驱动端轴承磨损，建议停机检查。",
  "riskLevel": "high",
  "confidence": null,
  "modelSource": "demo-model-v1",
  "evidence": {
    "documents": [
      {"name": "Atlas_Copco_GX11_UserManual_RevC.pdf", "version": "RevC", "page": 42, "score": 0.946}
    ]
  },
  "alertId": null
}
```

- `organization_id` 不在请求体，来自认证上下文。
- `confidence` 可空；C 无依据时传 `null`，不编造。

### 5.2 查询 `GET /api/v1/diagnoses`、`GET /api/v1/diagnoses/{id}`

分页 `{items, page, pageSize, total, totalPages}`；刷新可查已持久化字段。

## 6. 人工确认与建单（B，已实现）

`POST /api/v1/diagnoses/{diagnosis_id}/confirm`

请求 `DiagnosisConfirm`：

```json
{"title": "AC-07 驱动端轴承检查", "priority": "P1 紧急", "note": "已现场确认"}
```

- **确认人 = 登录用户**（`confirmedBy` 来自认证上下文），请求体无 `operator_id`。
- **幂等**：重复确认返回 200 + 原工单，不重复建单。
- 已拒绝诊断返回 409 `INVALID_STATE`。
- 响应 `{diagnosis, workOrder}`。

## 7. 审计（B，已实现）

`GET /api/v1/audit-events`

参数：`page` / `pageSize` / `action` / `entityType` / `entityId` / `actorId` / `from` / `to` / `q`。权限 `manager` 及以上。

## 8. 错误格式（B 定义）

```json
{"error": {"code": "NOT_FOUND", "message": "资源不存在", "details": null, "requestId": "……"}}
```

`code`：`VALIDATION_ERROR` / `UNAUTHORIZED` / `FORBIDDEN` / `NOT_FOUND` / `CONFLICT` / `INVALID_STATE` / `INVALID_TRANSITION` / `INTERNAL_ERROR`。

## 9. 端到端联调用例（AC-07 空压机）

**正常链路**：B 设备查询 `AC-07` → `/api/v1/chat` 提问 → 检索 `compressor-002` → 结构化结论与稳定引用 → `/api/v1/diagnoses` 保存 → `/confirm` 人工确认建单 → `/api/v1/audit-events` 可查 → 刷新仍正确、重复确认不重复建单。

**失败链路**：设备不存在、跨组织越权、设备编号不一致、设备服务超时、无文档、型号不匹配、模型不可用、非法引用，均返回明确 `status`，不伪造成功、不越权写入。

## 10. 联调记录

2026-10-22 已使用 B 侧 SQLite 种子数据完成 AC-07 设备事实、身份透传、跨组织隔离与模型不可用降级联调。命令、请求和实测结果见 [docs/integration-ac07.md](integration-ac07.md)。真实模型仍需配置密钥后复测。

C 侧文档上传、解析、检索与诊断演示见 [docs/demo-ac07.md](demo-ac07.md)，使用虚构演示文档，`is_demo=true`。
