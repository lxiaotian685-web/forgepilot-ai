# 制造领航 ForgePilot

面向中小制造企业设备维护的 Web 作品。系统把设备台账、测点、告警、知识文档、辅助诊断、维修工单和审计记录串成可演示的流程。

> 参赛方向：第九届传智杯 AI WEB 网页开发挑战赛。当前仓库使用**虚构演示数据**。企业数据和模型密钥尚未取得；默认诊断明确标记为模拟结果，不宣称接入真实企业设备或真实大模型。

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

三个进程分别运行。前端 API 模式只读取服务端数据；请求失败会提示错误，不会将本地虚构数据伪装成接口结果。B 服务的 PostgreSQL 迁移与 SQLite 本地演示均可用；C 服务目前使用单进程 JSON 知识库，部署多实例前须迁移存储。

## 本地复现

需要 Python 3.10+、Node.js 20+、npm；Windows 示例使用 PowerShell。首次安装依赖：

```powershell
cd services/business
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ../knowledge
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ../../frontend
npm ci
cd ..
```

运行本地三服务演示：

```powershell
.\scripts\start-demo.ps1
```

打开 `http://127.0.0.1:5180/forgepilot/`，使用仅限本地的虚构账号 `demo@example.com` / `ForgePilot123!`。停止：`.\scripts\stop-demo.ps1`。启动脚本为会话生成随机签名密钥、绑定回环地址并创建 SQLite 演示数据库。它只用于评审本地复现，不能原样公开部署。

Linux/macOS 的三终端命令见 [docs/RUN_LINUX.md](docs/RUN_LINUX.md)。

服务接口：业务 `http://127.0.0.1:8001/docs`、知识 `http://127.0.0.1:8002/docs`。各服务配置模板在 `services/business/.env.example`、`services/knowledge/.env.example`，前端配置模板在 `frontend/.env.example`；**模板值不能直接用于生产**。部署时后端设置独立密钥、受控 CORS、HTTPS 与身份校验，前端仅配置公开 API 地址，不包含模型密钥。

## 验证

```powershell
cd frontend; npm test; npm run build; cd ..
cd services/business; .\.venv\Scripts\python.exe -m pytest -q; .\.venv\Scripts\python.exe -m ruff check .; cd ../..
cd services/knowledge; .\.venv\Scripts\python.exe -m pytest -q; .\.venv\Scripts\python.exe -m ruff check .; cd ../..
```

模型配置成 `LLM_PROVIDER=openai`、提供合法密钥、模型与基础 URL，并使用 `DEVICE_PROVIDER=http` 读取 B 服务后，才能测试真实模型路径。无配置时 C 返回带 `is_mock`/降级状态的演示结果，前端不会把它作为可保存的真实诊断。

## 团队与来源

- 梁晓添：产品、前端、业务集成、后端补充与最终统筹。
- 林同学：业务后端早期开发；后续负责演示视频录制。
- 龚同学：知识检索、诊断服务与文档上传。
- 指导教师丁老师提供业务反馈；企业原始数据尚未授权使用。

原始 A/B/C 功能分支和各轮 Pull Request 保留细粒度开发历史。本集成分支把三个独立服务放入同一可复现仓库；来源记录见 [docs/SOURCE_COMMITS.md](docs/SOURCE_COMMITS.md)。协作要求见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 提交说明

校赛通知要求公开或授权评审访问的代码仓库、README、环境配置说明、完整细粒度 Git 历史、5–8 分钟普通话 1080p 演示视频和不超过 30 页的技术 PDF；在线演示为可选加分项。通知：[东莞理工学院计算机学院校赛公告](https://cs.dgut.edu.cn/info/1034/19118.htm)。A/B/C 功能与集成代码已合入 `main`；视频和 PDF 是独立提交材料，公网部署仍需另行配置，不能仅凭本地演示宣称已完成比赛提交。

代码使用 [MIT License](LICENSE)。虚构说明书用于演示；不要上传未获授权的企业资料、密钥或个人信息。
