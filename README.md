# 制造领航 ForgePilot

> 面向中小制造企业的设备知识、故障诊断与维护协同 AI Agent。

ForgePilot 希望把设备台账、说明书、维修记录、点检数据和备件信息连接起来，让一线人员可以用自然语言查询设备知识、获得有证据的诊断建议，并把结果转化为可追踪的维护任务。

本项目面向 Web 网站开发比赛的 **AI Agent智能助手** 与 **RAG知识问答系统** 方向，也是一个围绕数据库、工业业务流程和AI工程构建的工业软件作品集项目。

## 当前状态

当前仓库处于早期后端原型阶段。

已实现：

- FastAPI应用骨架与健康检查；
- 设备问答请求与响应数据模型，以及明确标记为 mock 的诊断接口；
- 设备、告警、工单业务 API（分页、筛选、权限、组织隔离、审计）；
- PostgreSQL 第一版 Alembic 迁移与虚构种子数据；
- API 自动化测试（pytest）覆盖 CRUD、权限、隔离和状态机。

尚未实现：

- Web前端；
- 说明书RAG知识库；
- 真实大模型与Agent工具调用；
- 备件、生产部署与完整权限体系。

完整方案、分工和里程碑见 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)。参与开发前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

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

### 数据库

本地演示默认使用 SQLite（`forgepilot.db`，已加入 `.gitignore`）：

```powershell
.\.venv\Scripts\python.exe -m app.seed
```

使用 PostgreSQL（团队集成 / 部署）：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,postgres]"
$env:DATABASE_URL="postgresql+psycopg://forgepilot:change-me@localhost:5432/forgepilot"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
```

回退：`.\.venv\Scripts\python.exe -m alembic downgrade base`

注意：PostgreSQL 必须先执行迁移再 seed；SQLite 演示由 `app.seed` 自动建表。环境变量参考 `.env.example`。

数据模型见 [docs/data-model/README.md](docs/data-model/README.md)，接口契约见 [docs/api-contracts/business-api.yaml](docs/api-contracts/business-api.yaml)。

## 当前接口

| 方法 | 路径 | 状态 | 用途 |
|---|---|---|---|
| GET | `/health` | 已实现 | 服务健康检查 |
| POST | `/api/v1/chat` | Mock | 接收设备ID和问题，返回模拟诊断结果 |
| GET | `/api/v1/devices` | 已实现 | 设备分页列表（筛选/分页） |
| GET | `/api/v1/devices/{device_id}` | 已实现 | 设备详情 |
| GET | `/api/v1/alerts` | 已实现 | 告警分页列表（筛选） |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | 已实现 | 确认告警 |
| GET | `/api/v1/work-orders` | 已实现 | 工单分页列表（筛选） |
| POST | `/api/v1/work-orders` | 已实现 | 创建工单 |
| PATCH | `/api/v1/work-orders/{work_order_id}` | 已实现 | 更新工单状态/负责人 |

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

