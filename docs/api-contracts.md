# 诊断与确认建单 API 契约（v1.1，已对齐 B 实现）

> 状态：C 侧契约，已对齐 B 的 `docs/api-contracts/business-api.yaml`（PR #16 实际实现）。
> 关联：Issue #12（C 有据诊断）、Issue #11（B 诊断持久化）、Issue #4（端到端闭环）。

## 1. 角色与边界

| 角色 | 职责 | 边界 |
|---|---|---|
| C | 检索、模型调用、返回证据 | 只读；不落库、不建单 |
| B | 设备事实、权限、诊断落库、确认建单、审计 | 写路径唯一入口 |
| A | 交互、页面反馈 | 不提交 `equipment_model` |

- 权威型号来自 B 的设备查询，C 不再复制维护一套型号表。
- 模型（C）不能直接建单，必须走 B 的确认接口。
- 组织与用户来自认证上下文，前端不在请求体传 `organization_id`。

## 2. 认证与权限（B 定义）

- 组织与用户来自**认证上下文**，不在 JSON 请求体。
- 演示模式：请求头 `X-Organization-Id`、`X-User-Id`；缺省回落到 demo 组织/用户。
- 生产模式：`Authorization: Bearer <token>`（token 内含 org/user，HMAC 签名）。
- 角色等级：`viewer < technician < manager < admin < owner`。
- 跨组织资源一律返回 404。

## 3. C 侧接口（只读）

### 3.1 诊断 `POST /api/v1/chat`

请求 `{device_id, question}`；响应 `{device_id, answer, statements, sources, is_mock, status}`。

`status`：`ok` / `no_answer` / `model_unavailable` / `device_not_found` / `no_knowledge` / `model_mismatch`。

### 3.2 检索与文档

- `POST /api/v1/search`、`POST /api/v1/documents/ingest`、`GET /api/v1/documents`。

## 4. C 侧证据引用扩展（待实现，本轮补）

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

### 4.3 `conflicts` 与 `verificationSuggestions`

- `conflicts`：设备事实与文档结论不一致时，同时展示双方来源，禁止静默覆盖。
- `verificationSuggestions`：说明缺什么证据、用于核验什么判断。
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

**正常链路**：设备告警 → `/api/v1/chat` 提问 → 带证据结论 → `/api/v1/diagnoses` 保存 → `/confirm` 人工确认建单 → `/api/v1/audit-events` 可查 → 刷新仍正确、重复确认不重复建单。

**失败链路**：无文档、型号不匹配、模型不可用、未授权访问，均有明确反馈，不伪造成功、不越权写入。
