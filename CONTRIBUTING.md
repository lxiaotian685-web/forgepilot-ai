# 参与制造领航开发

## 工作流程

1. 在 GitHub Issue 中认领任务并确认验收标准。
2. 从最新 `main` 创建短生命周期分支。
3. 完成功能、测试和必要文档。
4. 推送分支并创建 Pull Request。
5. 项目统筹人核对改动、测试和集成结果后决定合并；成员意见和未解决的问题写在 PR 中。

## 分支命名

- `feature/<功能>`：新功能，例如 `feature/equipment-registry`
- `fix/<问题>`：缺陷修复，例如 `fix/chat-validation`
- `docs/<内容>`：文档，例如 `docs/architecture`
- `test/<范围>`：测试，例如 `test/work-order-api`
- `chore/<内容>`：工程配置，例如 `chore/ci`

## 提交信息

```text
feat: add equipment registry API
fix: reject unknown device ids
docs: describe RAG evidence model
test: cover work order transitions
```

## Pull Request 检查

- 说明解决的问题和设计选择；
- 关联对应 Issue；
- 列出测试命令与实际结果；
- API变化提供请求/响应示例；
- 数据库变化提供迁移与回退说明；
- UI变化提供截图或录屏；
- 确认没有密钥和企业敏感数据。

## 本地质量检查

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

## 数据与AI规则

- 关键设备参数必须保存在结构化字段中，并记录来源；
- RAG回答必须返回文档与页码/分块证据；
- Agent不得直接执行高风险设备操作；
- AI输出必须区分事实、推断和待人工确认项；
- 示例企业数据必须虚构或完成脱敏。

