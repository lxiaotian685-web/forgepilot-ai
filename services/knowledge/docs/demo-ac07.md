# AC-07 文档上传与检索演示记录

> 本文件使用虚构演示数据，不含真实企业文档、个人信息或未脱敏资料。
> 用途：C 侧文档上传、解析、检索、诊断联调与 A/B 交接。

## 演示文档

| 字段 | 值 |
|---|---|
| 文件 | `data/demo_uploads/ac07_upload_demo.txt` |
| 标题 | AC-07 现场维护补充说明（演示上传） |
| 设备型号 | `compressor-002` |
| 版本 | `1.0` |
| 组织 | `demo-org` |
| 页数 | 4 |
| 分块数 | 4 |

## 上传

演示环境临时开启写接口：

```powershell
$env:C_ENABLE_INGEST = "true"
$env:C_API_BASE_URL = "http://127.0.0.1:8010"  # 示例端口，可按实际修改
$env:C_DEFAULT_ORGANIZATION_ID = "demo-org"
.\.venv\Scripts\python.exe -m scripts.upload_demo
```

> `document_id` 和检索分数是单次实测记录；重新上传或重建知识库后会变化。
> 页码、标题和分块定位应保持稳定。

实测上传响应：

```json
{
  "document_id": "f2074e9f20d545e5",
  "title": "AC-07 现场维护补充说明（演示上传）",
  "equipment_model": "compressor-002",
  "version": "1.0",
  "source": "ac07_upload_demo.txt",
  "page_count": 4,
  "chunk_count": 4
}
```

## 检索结果

请求：

```json
{
  "query": "排气温度过高",
  "equipment_model": "compressor-002",
  "top_k": 3
}
```

实测 top3：

| 排名 | 文档 | 页码 | 分数 |
|---|---|---|---|
| 1 | AC-07 现场维护补充说明（演示上传） | 2 | 6.5084 |
| 2 | 空压机维修规范 | 2 | 6.3992 |
| 3 | AC-07 现场维护补充说明（演示上传） | 4 | 3.0787 |

第一条证据 ID：`f2074e9f20d545e5@1.0#p2c1`，可定位到文档、版本、页码和分块。

## 诊断结果

请求：

```json
{
  "device_id": "AC-07",
  "question": "排气温度过高怎么排查？"
}
```

实测：

- `status=ok`
- `is_mock=true`
- `device_source=static`
- `is_demo=true`
- 返回 3 条证据
- 3 条 `fact`，每条 `source_ids` 均能在本次 `sources` 中找到
- 另有 `inference` 和 `pending` 各 1 条

> 本次联调使用 MockLLM 和 static 设备提供方，`is_demo=true`。
> 真实模型与真实 B 设备联调需配置密钥和 `DEVICE_PROVIDER=http` 后复测；
> 只有 `status=ok` 且 `is_demo=false` 才能视为真实诊断成功。

真实 B 设备事实、身份透传、跨组织隔离与模型不可用降级记录见
[docs/integration-ac07.md](integration-ac07.md)。上传文档后，C 会继续按
B 返回设备对应的知识域检索。

## PDF 支持

- 支持 PDF、TXT、MD 上传
- PDF 仅提取可复制文本；扫描件/纯图片 PDF 需要 OCR，当前不支持
- 上传接口默认关闭，生产环境必须保持 `C_ENABLE_INGEST=false`
- 组织编号从 `X-Organization-Id` 获取，不能由表单指定
