# 真实 RAG 验证报告

- 日期：2026-10-28
- 服务：`services/knowledge`
- 分支：`task/gong-real-rag`
- 状态：**虚构数据集验证完成；真实企业资料和真实模型调用尚未验证**

> 本报告只使用虚构或已脱敏演示数据，不包含真实企业文档、个人信息或模型密钥。
> 没有模型密钥和授权企业资料时，不能把本报告视为企业 RAG 验收完成。

## 1. 验证范围

| 能力 | 状态 |
|---|---|
| TXT/MD/PDF 上传 | 已实现并测试 |
| PDF 按页解析、页码保留 | 已实现并测试 |
| 组织隔离 | 已实现并测试 |
| 设备型号/知识域隔离 | 已实现并测试 |
| 文档版本与稳定证据 ID | 已实现并测试 |
| 原文片段、标题、版本、页码/分块 | 已实现并测试 |
| 无证据时明确 `no_answer` | 已实现并测试 |
| 模型超时/鉴权/不可用降级 | 已实现并测试 |
| 真实模型调用 | **未验证**（无密钥） |
| 企业授权资料验收 | **未验证**（无授权资料） |
| 扫描件/图片 PDF OCR | **不支持** |

## 2. 虚构数据集

| 文件 | 标题 | 型号 | 页数 |
|---|---|---|---|
| `data/demo_docs/air_compressor.txt` | 空压机维修规范 | `compressor-002` | 4 |
| `data/demo_docs/centrifugal_pump.txt` | 离心泵维护手册 | `pump-004` | 4 |
| `data/demo_docs/cnc_safety.txt` | 数控机床安全操作规范 | `cnc-003` | 4 |
| `data/demo_uploads/ac07_upload_demo.txt` | AC-07 现场维护补充说明（演示上传） | `compressor-002` | 4 |

评测集：`evaluation/eval_set.json`，共 20 条问题，其中 16 条有答案、4 条无答案。

演示上传与检索记录见 [demo-ac07.md](demo-ac07.md)；AC-07 与 B 服务的设备事实联调见 [integration-ac07.md](integration-ac07.md)。

## 3. 自动化验证结果

在本目录执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m scripts.evaluate
```

实测结果：

```text
pytest: 129 passed
ruff: All checks passed
RAG 评测:
  可答问题数: 16
  命中率 (期望文档进入 top3): 16/16 = 100.0%
  引用准确率 (期望页码进入 top3): 16/16 = 100.0%
  无答案准确率: 4/4 = 100.0%
```

## 4. 证据可追溯性

`ChatResponse.sources` 中每条证据包含：

```json
{
  "id": "a1b2c3d4e5f6@1.0#p2c1",
  "document_id": "a1b2c3d4e5f6",
  "organization_id": "demo-org",
  "version": "1.0",
  "title": "空压机维修规范",
  "page": 2,
  "chunk_index": 1,
  "snippet": "排气温度过高排查：冷却器、油位。",
  "score": 6.3992
}
```

- `id` 可定位到文档、版本、页码和分块。
- `page` 允许为 `null`；为空时 `statement.source` 显示“未知页”，不编造页码。
- `fact` 的 `source_ids` 必须命中本次 `sources`；否则降级为 `pending`，整体返回 `no_answer`。
- `statement.source` 由 C 根据有效证据重新生成，不采用模型自填来源。

## 5. 模型接入与失败路径

模型配置只从服务端环境变量读取：

```text
LLM_PROVIDER=openai
LLM_API_KEY=<仅服务端>
LLM_BASE_URL=<OpenAI 兼容地址>
LLM_MODEL=<模型名>
LLM_TIMEOUT=30
LLM_MAX_TOKENS=1024
HTTP_TRUST_ENV=false
```

已覆盖的模型失败测试：

- 结构化 JSON 正常输出
- Markdown code fence 包裹 JSON
- 非法 JSON
- schema 不匹配
- 超时
- 缺少 `LLM_API_KEY` / `LLM_BASE_URL`
- HTTP 401 / 403（鉴权失败）
- HTTP 429（限流）
- HTTP 500（上游不可用）
- 模型 HTTP 响应体不是合法 JSON
- 设备事实进入模型上下文
- 提示注入防护

模型失败时：

- 返回 `status=model_unavailable`
- 保留检索证据和 `pending` 提示
- 不返回伪造的成功结论
- `is_mock=false` 但 `status` 明确为降级，前端不得把它显示为成功

## 6. 未完成的真实接入验证

| 项目 | 原因 | 需要补充 |
|---|---|---|
| 真实 OpenAI 兼容模型 | 当前环境没有模型密钥 | 配置服务端密钥后执行 AC-07 诊断，确认 `is_mock=false`、`status=ok` |
| 企业 RAG | 尚未取得授权企业资料 | 使用授权且脱敏的资料建立评测集，复测命中率、引用准确率和无答案率 |
| 扫描件/图片 PDF | 需要 OCR | 接入 OCR 后再验收 |
| 向量/混合检索 | 当前离线 BM25 | 数据规模增大后评估 pgvector/混合检索 |

真实模型验收命令示例（不要把密钥写入仓库）：

```powershell
$env:APP_ENV = "development"
$env:LLM_PROVIDER = "openai"
$env:LLM_API_KEY = "<服务端密钥>"
$env:LLM_BASE_URL = "<OpenAI 兼容地址>"
$env:LLM_MODEL = "<模型名>"
$env:DEVICE_PROVIDER = "http"
$env:DEVICE_API_BASE_URL = "http://127.0.0.1:8001"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

然后调用 `/api/v1/chat`，确认：

- `status=ok`
- `is_mock=false`
- `is_demo=false`
- 每条 `fact` 的 `source_ids` 都能在 `sources` 中定位
- 无证据问题返回 `no_answer`
- 可使用第 7 节的 `scripts.verify_real_rag` 自动检查以上条件

## 7. 真实模型验收脚本

服务以真实模型和 B 设备事实启动后，可直接运行：

```powershell
$env:C_API_BASE_URL = "http://127.0.0.1:8002"
$env:C_ORGANIZATION_ID = "<当前组织>"
$env:C_USER_ID = "<当前用户>"
$env:C_API_TOKEN = "<Bearer 令牌，可选>"
.\.venv\Scripts\python.exe -m scripts.verify_real_rag
```

脚本检查：

- `/health` 的 `llm_provider=openai`、`device_provider=http`
- AC-07 诊断 `status=ok`、`is_mock=false`、`is_demo=false`
- 每条 `sources` 包含 ID、文档、版本、标题、页码、分块、片段和分数
- 每条 `fact` 的 `source_ids` 都命中本次 `sources`
- 无答案问题返回 `no_answer` 且不携带证据
- 页码未知时允许 `page=null`，但 `statement.source` 必须显示“未知页”

脚本在 Mock/static、`is_demo=true`、证据缺失或引用越界时返回非零退出码，不能把演示结果当作真实验收。

## 8. 结论

- 虚构数据集上的上传、解析、检索、引用和降级链路已通过自动化验证。
- 当前结果不能声称为真实企业 RAG 或真实模型诊断。
- 等模型密钥和授权企业资料到位后，按第 6、7 节复测并更新本报告，才能完成真实 RAG 验收。
