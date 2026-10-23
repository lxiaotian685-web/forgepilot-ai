# AC-07 C ↔ B 联调记录

- 日期：2026-10-22
- 范围：C 侧 `/api/v1/chat` ↔ B 侧 `GET /api/v1/devices/{device_id}`
- 模型：MockLLM（`is_mock=true`）；真实模型待配置密钥后复测
- 数据库：B 侧本地 SQLite + `app.seed` 虚构数据
- 身份：演示模式 `X-Organization-Id` / `X-User-Id`，由 C 按请求透传

## 启动方式

B 侧：

```powershell
$env:DATABASE_URL = "sqlite+pysqlite:///./forgepilot.db"
$env:AUTH_MODE = "demo"
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

C 侧：

```powershell
$env:APP_ENV = "development"
$env:DEVICE_PROVIDER = "http"
$env:DEVICE_API_BASE_URL = "http://127.0.0.1:8001"
$env:LLM_PROVIDER = "mock"
$env:C_REQUIRE_AUTH = "true"
$env:C_ENABLE_INGEST = "false"
$env:RATE_LIMIT_PER_MINUTE = "0"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

## 联调请求

```python
import httpx

headers = {
    "X-Organization-Id": "demo-org",
    "X-User-Id": "tech@example.com",
}
response = httpx.post(
    "http://127.0.0.1:8002/api/v1/chat",
    json={"device_id": "AC-07", "question": "排气温度过高怎么排查？"},
    headers=headers,
    timeout=30,
)
print(response.json())
```

## 实测结果

| 场景 | 请求身份 | 结果 |
|---|---|---|
| AC-07 正常诊断 | `demo-org` / `tech@example.com` | HTTP 200，`status=ok`，`device_source=http`，`is_demo=true`（MockLLM），3 条证据，5 条陈述，首条来源为《空压机维修规范》第 2 页 |
| 缺少组织头 | 无 `X-Organization-Id` | HTTP 401，未进入诊断 |
| 跨组织设备 | `northwind-org` / `other@example.com` | HTTP 404，`status=device_not_found`，0 证据，不泄漏设备存在性 |
| 组织与用户不匹配 | `northwind-org` / `tech@example.com` | HTTP 403，`status=device_unauthorized`，0 证据 |
| 不存在的设备 | `demo-org` / `tech@example.com`，`device_id=AC-99` | HTTP 404，`status=device_not_found`，0 证据 |
| 模型不可用 | `demo-org` / `tech@example.com` | HTTP 200，`status=model_unavailable`，仍返回 3 条检索证据与待确认项 |
| B 返回其他设备 ID | 单元测试模拟 | HTTP 502，`status=device_mismatch`，拒绝使用该设备事实 |

## 结论

- C 侧已通过真实 HTTP 调用 B 包的 AC-07 设备详情，设备事实不再依赖静态 `DEVICE_CATALOG`。
- 请求级身份透传生效；缺少组织头返回 401，跨组织返回 404，越权返回 403，不伪造成功。
- 检索证据与设备知识域映射生效：`GX11 → compressor-002`；事实来源由 C 根据 `source_ids` 重新生成。
- 响应通过 `device_source=http` 和 `is_demo=true` 明确标记设备来源与 Mock 模型，避免把演示结果当成真实成功。
- 真实模型调用尚未执行，需在配置 `LLM_PROVIDER=openai`、`LLM_BASE_URL`、`LLM_MODEL` 和密钥后复测。
- `device_mismatch` 因 B 正常不会返回错误 ID，使用 `httpx.MockTransport` 单元测试覆盖。
