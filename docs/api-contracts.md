# 诊断与确认建单 API 契约（v1 草案）

> 状态：待三方评审。本文由 C 起草，B 负责写路径（落库/确认/审计），A 负责交互调用。
> 关联：Issue #12（C 有据诊断）、Issue #11（B 诊断持久化）、Issue #4（端到端闭环）。

## 1. 角色与边界

| 角色 | 职责 | 边界 |
|---|---|---|
| C | 检索、模型调用、返回证据 | 只读，无副作用；不落库、不建单 |
| B | 设备事实、权限、诊断落库、确认建单、审计 | 写路径唯一入口；跨设备/跨组织校验 |
| A | 交互、页面反馈 | 不提交 `equipment_model` 覆盖设备档案 |

关键约定：

- 权威型号来自 B 的设备查询，C 不再维护一套型号表。
- 模型（C）不能直接建单，必须走 B 的人工确认接口。
- 前端不传 `equipment_model`；设备身份由 `device_id` 决定。

## 2. 已上线接口（保持兼容，字段只增不删）

### 2.1 诊断 `POST /api/v1/chat`

请求：

```json
{"device_id": "AC-07", "question": "排气温度过高怎么排查？"}
```

响应（现状）：

```json
{
  "device_id": "AC-07",
  "answer": "基于知识库检索，给出以下模拟诊断建议……",
  "statements": [
    {"type": "fact", "text": "……", "source": "《空压机维修规范》第2页"}
  ],
  "sources": [
    {"document_id": "a1b2c3d4", "title": "空压机维修规范", "page": 2, "snippet": "……", "score": 5.21}
  ],
  "is_mock": true,
  "status": "ok"
}
```

`status` 取值：`ok` / `no_answer` / `model_unavailable` / `device_not_found` / `no_knowledge` / `model_mismatch`。

### 2.2 检索与文档

- `POST /api/v1/search`：请求 `{query, equipment_model?, top_k?}`，返回 `{query, count, results}`。
- `POST /api/v1/documents/ingest`、`GET /api/v1/documents`：文档入库与列表。

## 3. 本轮待补：证据引用与诊断响应扩展（C 负责）

目标：每条引用可核查，区分「文档事实 / 模型推断 / 待验证项」，冲突展示双方来源。

### 3.1 稳定引用 ID

每条 `source` 增加稳定、可回查的字段（新增，不删旧字段）：

```json
{
  "id": "a1b2c3d4@v1.0#p2",
  "document_id": "a1b2c3d4",
  "version": "1.0",
  "page": 2,
  "title": "空压机维修规范",
  "snippet": "……",
  "score": 5.21
}
```

- `id` 由 `document_id + 文档版本 + 页码/分块` 组成，稳定可追溯。
- `page` 允许为 `null`，未知页码必须标 `null`，不得编造页码。

### 3.2 Statement 扩展

每条 `statement` 增加 `source_ids`，指向本次检索结果的稳定引用（只允许指向本次返回的 `sources`）：

```json
{"type": "fact", "text": "……", "source": "《空压机维修规范》第2页", "source_ids": ["a1b2c3d4@v1.0#p2"]}
```

- `type`：`fact`（文档事实）/ `inference`（模型推断）/ `pending`（待人工验证）。
- 模型生成的引用若不在本次 `sources` 中，视为错误引用，必须过滤或标记。

### 3.3 conflicts（冲突）

当设备事实（B）与文档结论（C）不一致时，同时展示双方来源：

```json
{
  "conflicts": [
    {
      "field": "额定排气压力",
      "sources": [
        {"origin": "device_record", "value": "0.8 MPa", "ref": "设备档案 AC-07"},
        {"origin": "document", "value": "0.7 MPa", "ref": "a1b2c3d4@v1.0#p1"}
      ]
    }
  ]
}
```

禁止静默覆盖；禁止自动修改设备参数。

### 3.4 verificationSuggestions（补采建议）

说明缺什么证据、用于核验什么判断，不显示虚构概率：

```json
{
  "verificationSuggestions": [
    {"missing_evidence": "最近一次冷却器清洗记录", "to_verify": "判断冷却器堵塞是否是本次温度过高的主因"}
  ]
}
```

### 3.5 扩展后完整响应（示例）

```json
{
  "device_id": "AC-07",
  "answer": "……",
  "statements": [
    {"type": "fact", "text": "……", "source": "《空压机维修规范》第2页", "source_ids": ["a1b2c3d4@v1.0#p2"]},
    {"type": "inference", "text": "……", "source": null, "source_ids": ["a1b2c3d4@v1.0#p2"]},
    {"type": "pending", "text": "……", "source": null, "source_ids": []}
  ],
  "sources": [
    {"id": "a1b2c3d4@v1.0#p2", "document_id": "a1b2c3d4", "version": "1.0", "page": 2, "title": "空压机维修规范", "snippet": "……", "score": 5.21}
  ],
  "conflicts": [],
  "verificationSuggestions": [],
  "is_mock": true,
  "status": "ok"
}
```

## 4. 诊断保存与查询（B 负责）

C 的诊断结果作为 B 落库的输入。B 需保存：组织、设备、输入问题、结论、引用快照、模型来源与状态。

### 4.1 保存 `POST /api/v1/diagnoses`

请求（B 内部组装，含权限上下文）：

```json
{
  "organization_id": "org-01",
  "device_id": "AC-07",
  "question": "排气温度过高怎么排查？",
  "answer": "……",
  "statements": ["……快照……"],
  "sources": ["……快照……"],
  "model_source": "mock-llm",
  "is_mock": true,
  "status": "ok"
}
```

响应：`{"diagnosis_id": "dg-xxxx", "created_at": "……"}`。

### 4.2 查询 `GET /api/v1/diagnoses/{diagnosis_id}`

返回诊断记录与关联工单状态，刷新页面仍能看到正确关联。

## 5. 人工确认与建单（B 负责）

`POST /api/v1/diagnoses/{diagnosis_id}/confirm`

请求：

```json
{"operator_id": "user-01", "notes": "确认按建议停机检查冷却器"}
```

约束：

- `operator_id` 必填，人工确认必须有操作者。
- 幂等：重复确认返回同一张工单，不重复建单。
- 事务：确认 + 建单原子提交，失败不留半条业务链。
- 同组织、同设备校验，拒绝跨设备、跨组织关联。

响应：`{"work_order_id": "wo-xxxx", "status": "created"}`。

## 6. 审计查询（B 负责）

`GET /api/v1/audit-logs?diagnosis_id=&organization_id=&actor_id=`

返回操作者、时间、动作、前后状态，供刷新与回溯。

## 7. 错误码约定

| HTTP | status / detail | 场景 |
|---|---|---|
| 200 | `status` 见 2.1 | 正常诊断（含 no_answer 等）|
| 404 | `device_not_found` | 设备不存在 |
| 409 | `model_mismatch` | 型号与设备档案不一致 |
| 409 | `duplicate_confirm` | 重复确认（返回已有工单）|
| 403 | `forbidden` | 跨组织/越权访问 |
| 503 | `model_unavailable` | 模型服务不可用 |

> 具体 HTTP 状态码以 B 实现为准，C 的 `/api/v1/chat` 当前统一以 200 + `status` 返回，`model_mismatch` 等是否改为 4xx 由三方在评审中确认。

## 8. ID 与文件边界

- `device_id`、`organization_id`、`diagnosis_id`、`work_order_id` 的命名与类型以 B 数据库为准。
- 稳定引用 `id` 由 C 生成，规则见 3.1；B 落库时原样保存引用快照。
- 页码未知用 `null`，不得用 0 或 1 占位。

## 9. 端到端联调用例（AC-07 空压机）

**正常链路**：设备告警 → 提问 → 带证据结论 → 人工确认 → 生成工单 → 审计可查 → 刷新仍正确、重复确认不重复建单。

**失败链路**：无文档 → 型号不匹配 → 模型不可用 → 未授权访问，均有明确反馈，不伪造成功、不越权写入。
