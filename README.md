# 制造领航 ForgePilot

面向中小制造企业设备维护的 Web 作品。系统把设备台账、测点、告警、知识文档、辅助诊断、维修工单和审计记录串成可演示的流程。

> 参赛方向：第九届传智杯 AI WEB 网页开发挑战赛。当前仓库使用**虚构演示数据**。企业数据和模型密钥尚未取得；默认诊断明确标记为模拟结果，不宣称接入真实企业设备或真实大模型。

## 立即体验

直接打开 [CloudBase 在线演示](https://cloud1-d8gmw1jur6dc98110-1470332055.tcloudbaseapp.com/forgepilot-preview/)，无需下载代码或安装软件。该地址提供前端演示数据；操作仅用于体验页面流程，不会写入云端业务数据库。ICP备案未完成期间，CloudBase 默认域名可能有访问提示或限制。

要在 Windows 本地运行前后端完整演示，预先安装 **Python 3.10+**、**Node.js 20+**（含 npm）和 **PowerShell 7.4+**，在仓库根目录执行：

```powershell
.\scripts\quickstart.ps1
```

首次运行会自动建立两个 Python 虚拟环境、安装依赖并启动三个服务，之后打开 `http://127.0.0.1:5180/forgepilot/`。本地演示账号为 `demo@example.com` / `ForgePilot123!`；停止服务运行 `.\scripts\stop-demo.ps1`。本地演示使用 SQLite 和虚构数据，**不需要** PostgreSQL、CloudBase、企业数据或模型密钥。

## 体验路线

1. 用评审演示账号登录，选择 `AC-07` 空压机，查看该设备的测点与历史。
2. 在告警中心创建、指派并处理告警；在工单页面创建、指派、处理和验收维修任务。
3. 上传虚构说明书，核对解析文本、删除误上传文档；在诊断工作台查看证据、冲突和待补采项。
4. 只有非模拟且符合证据校验的诊断才允许保存；之后由人确认并生成工单，审计记录可追溯操作。

设备导入支持 CSV 和扫码内容录入。扫码摄像头需要浏览器支持 `BarcodeDetector`，同时提供手动粘贴二维码内容。人员管理包含岗位、状态和停用前未完成工单转派。维修人员可查看看板与日历中的任务。

## 架构

| 目录 | 技术 | 职责 |
|---|---|---|
| `frontend/` | React、Vite、Fluent UI | 设备、告警、诊断、知识、工单、人员和审计页面 |
| `services/business/` | FastAPI、SQLAlchemy、Alembic | 登录、组织权限、设备、测点、告警、工单、诊断保存和审计 |
| `services/knowledge/` | FastAPI、BM25、可选 OpenAI 兼容模型 | 说明书解析检索、证据引用、辅助诊断；通过业务服务验证身份 |

知识服务的 `POST /api/v1/agent/assist` 提供受控只读 Agent 流程：先验证设备身份，再读取同设备历史工单并调用证据诊断，返回每一步工具状态。此接口不创建或修改工单；诊断保存与建单仍须在业务服务中人工确认。默认演示配置的模型与资料仍是模拟数据。
Agent 的历史工单工具需要 C 服务配置 `BUSINESS_API_BASE_URL`，并逐请求透传当前 Bearer 令牌和组织身份；未配置或查询失败时会明确显示该步骤不可用。B/C 两端配置相同的随机 `AGENT_AUDIT_KEY` 后，C 会把工具名称、状态和数量写入 B 的审计表，不发送提问原文或模型回答；如 B 设置了 `WRITE_API_KEY`，C 还需配置 `BUSINESS_WRITE_KEY`。前端诊断页会显示审计是否写入；公开预览只展示标注为演示的本地版本。

三个进程分别运行。前端 API 模式只读取服务端数据；请求失败会提示错误，不会将本地虚构数据伪装成接口结果。B 服务的 PostgreSQL 迁移与 SQLite 本地演示均可用；C 服务目前使用单进程 JSON 知识库，部署多实例前须迁移存储。

数据库准备使用 `scripts/prepare-business-db.ps1`：先在终端设置 PostgreSQL `DATABASE_URL`，再运行脚本执行 Alembic 迁移；仅开发演示环境可加 `-SeedDemo`。业务服务的 `/ready` 会实际查询数据库，适合部署就绪检查。`scripts/start-demo.ps1` 则继续使用独立的 SQLite 本地演示库。具体步骤见 [数据库运行说明](docs/DATABASE_READINESS.md)。

公网部署前，应分别在业务服务和知识服务的环境中执行 `python scripts/check_production_config.py business` 与 `python scripts/check_production_config.py knowledge`。脚本只检查必填配置，不打印密钥，也不能代替 PostgreSQL 迁移、模型调用、持久化卷和公网接口的实际验收。知识服务当前使用单进程 JSON 文件，部署时须将 `KNOWLEDGE_STORAGE_PATH` 指向持久化卷并保持单实例；多实例需要先改造存储。

## 本地复现与部署

首次安装或依赖需要更新时运行 `.\scripts\quickstart.ps1`；依赖已安装后可直接运行 `.\scripts\start-demo.ps1`。启动脚本为会话生成随机签名密钥、绑定回环地址并创建 SQLite 演示数据库，不能原样公开部署。

Linux/macOS 的三终端命令见 [docs/RUN_LINUX.md](docs/RUN_LINUX.md)。

服务接口：业务 `http://127.0.0.1:8001/docs`、知识 `http://127.0.0.1:8002/docs`。各服务配置模板在 `services/business/.env.example`、`services/knowledge/.env.example`，前端配置模板在 `frontend/.env.example`；**模板值不能直接用于生产**。部署时后端设置独立密钥、受控 CORS、HTTPS 与身份校验，前端仅配置公开 API 地址，不包含模型密钥。

真实后端上线时才需要 PostgreSQL、持久化文件存储和模型配置；CloudBase 步骤见 [后端部署说明](docs/CLOUDBASE_DEPLOY.md)。

## 验证

```powershell
cd frontend; npm test; npm run build; cd ..
cd services/business; .\.venv\Scripts\python.exe -m pytest -q; .\.venv\Scripts\python.exe -m ruff check .; cd ../..
cd services/knowledge; .\.venv\Scripts\python.exe -m pytest -q; .\.venv\Scripts\python.exe -m ruff check .; cd ../..
```

模型配置成 `LLM_PROVIDER=openai`、提供合法密钥、模型与基础 URL，并使用 `DEVICE_PROVIDER=http` 读取 B 服务后，才能测试真实模型路径。无配置时 C 返回带 `is_mock`/降级状态的演示结果，前端不会把它作为可保存的真实诊断。

知识服务的虚构数据集验证、引用样本、模型失败路径和未完成项见 [真实 RAG 验证报告](services/knowledge/docs/real-rag-report.md)。报告明确说明：真实企业资料和真实模型调用尚未完成，不能把当前演示结果当作企业诊断。

## 团队与来源

- 梁晓添：产品、前端、业务集成、后端补充与最终统筹。
- 林同学：业务后端早期开发；后续负责演示视频录制。
- 龚同学：知识检索、诊断服务与文档上传。
- 指导教师丁老师提供业务反馈；企业原始数据尚未授权使用。

原始 A/B/C 功能分支和各轮 Pull Request 保留细粒度开发历史。本集成分支把三个独立服务放入同一可复现仓库；来源记录见 [docs/SOURCE_COMMITS.md](docs/SOURCE_COMMITS.md)。协作要求见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 提交说明

校赛通知要求公开或授权评审访问的代码仓库、README、环境配置说明、完整细粒度 Git 历史、5–8 分钟普通话 1080p 演示视频和不超过 30 页的技术 PDF；在线演示为可选加分项。通知：[东莞理工学院计算机学院校赛公告](https://cs.dgut.edu.cn/info/1034/19118.htm)。A/B/C 功能与集成代码已合入 `main`；视频和 PDF 是独立提交材料，公网部署仍需另行配置，不能仅凭本地演示宣称已完成比赛提交。

代码使用 [MIT License](LICENSE)。虚构说明书用于演示；不要上传未获授权的企业资料、密钥或个人信息。
