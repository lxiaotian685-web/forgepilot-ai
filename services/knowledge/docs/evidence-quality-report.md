# RAG 证据质量与失败场景评测报告

- 日期：2026-11-08
- 分支：`task/c-r8-evidence-quality`
- 服务：`services/knowledge`
- 范围：版本过滤、重复切片去重、证据不足、无匹配资料、模型超时和鉴权失败
- 原则：只进分支和离线报告，不部署 Cloud Run，不改变前端主响应结构

> 本报告只使用虚构演示数据。引用一致性使用确定性 MockLLM 验证；
> 模型超时和鉴权失败使用 `httpx.MockTransport` 模拟。
> 真实模型和授权企业资料尚未验证。

## 1. 本轮代码改动

| 能力 | 实现 |
|---|---|
| 文档版本过滤 | `/api/v1/search` 和 `/api/v1/chat` 增加可选 `version`；检索候选和索引缓存都按版本隔离 |
| 重复切片去重 | 同一组织、同一版本下，规范化文本相同的切片只保留分数最高的一条 |
| 证据不足降级 | 模型没有给出任何可核实 `fact` 时，返回 `no_answer`，不保留推断性结论 |
| 评测集 | `evaluation/evidence_quality.json` |
| 评测脚本 | `scripts/evaluate_evidence_quality.py` |

前端主响应结构未变；只增加了可选请求字段和更严格的降级状态。

## 2. 评测命令

```powershell
cd services/knowledge
..\..\.venv\Scripts\python.exe -m scripts.evaluate_evidence_quality
```

## 3. 实测结果

| 指标 | 结果 |
|---|---|
| 检索命中（期望文档和页码进入 top3） | 3/3 = 100.0% |
| 引用一致性（fact 引用全部命中 sources） | 3/3 = 100.0% |
| 无匹配资料（应返回空结果） | 1/1 = 100.0% |
| 重复切片 | 0 条（去重后返回 1 条） |
| 版本过滤 | PASS |
| 证据不足降级 | PASS（`no_answer`，保留证据） |
| 模型超时降级 | PASS（`model_unavailable`，保留证据） |
| 模型鉴权失败降级 | PASS（`model_unavailable`，保留证据） |

## 4. 指标口径

- **检索命中**：期望文档和页码是否进入 top3，不代表诊断正确。
- **引用一致性**：每条 `fact` 的 `source_ids` 是否全部命中本次 `sources`，
  且 `source` 由有效证据反推生成。
- **降级结果**：无匹配资料返回 `no_answer`；模型超时/鉴权失败返回
  `model_unavailable`，并保留检索证据和待确认提示。
- **重复切片**：同一组织、同一版本内，规范化文本相同的片段只保留一条。

本报告不把检索命中率称为诊断准确率，也不把 MockLLM 结果称为真实模型结论。

## 5. 回归结果

```text
pytest: 140 passed
ruff: All checks passed
RAG 评测: 16/16 命中、16/16 引用、4/4 无答案
```

## 6. 已知边界

- 引用一致性使用 MockLLM 验证；真实模型仍需服务端密钥后复测。
- 真实企业资料尚未取得，当前只使用虚构演示数据。
- 检索仍为 BM25，未接入向量或混合检索。
- 引用一致性只校验 `source_ids` 是否命中 `sources`，不校验模型陈述与原文的语义蕴含。
- 扫描件/图片 PDF 不支持 OCR。
- 本轮不部署 Cloud Run，不合并 main，不修改线上版本。

## 7. 结论

- 版本过滤、重复切片去重和证据不足降级已实现并有自动化测试。
- 检索命中、引用一致性和降级结果已分开报告。
- 真实模型和真实企业数据仍是未完成项，不能把本报告当作企业 RAG 验收。
