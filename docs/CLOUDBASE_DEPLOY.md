# CloudBase 后端部署准备

当前 CloudBase 环境 `cloud1-d8gmw1jur6dc98110` 的静态托管已上线；截至 2026 年 10 月 29 日，云托管服务列表为空，CLI 查询 PostgreSQL 返回 `PG instance not found`。因此目前只有前端演示，不应把预览地址描述为完整的公网系统。

## 需要先开通的资源

1. 在同一 CloudBase 环境开通 PostgreSQL，取得供业务服务使用的连接信息。用独立账号和数据库运行 Alembic 迁移；不要用演示库或示例口令。
2. 为知识服务配置持久化文件存储，例如 CloudBase Run 支持的 CFS 挂载。将 `KNOWLEDGE_STORAGE_PATH` 指向挂载目录中的 JSON 文件；现有知识库是单进程文件存储，只能先部署一个实例。扩容前需改造为共享数据库或增加跨进程一致性控制。
3. 准备服务端模型地址、模型名与密钥，并配置 HTTPS 访问入口。模型密钥不得写入仓库或前端环境变量。

## 容器构建

业务与知识服务各有独立 `Dockerfile`，监听 CloudBase Run 提供的 `PORT`，默认 8080。构建上下文分别为 `services/business` 与 `services/knowledge`。`.dockerignore` 排除本地虚拟环境、测试缓存、演示数据库和知识库数据。

在已有 Docker 的机器上可先运行：

```powershell
docker build -t forgepilot-business ./services/business
docker build -t forgepilot-knowledge ./services/knowledge
```

本仓库不会在容器启动时自动执行数据库迁移。部署业务服务前，先在受控环境配置 `DATABASE_URL`，运行 `scripts/prepare-business-db.ps1`，再检查业务服务 `/ready`。迁移应只执行一次，不能由每个云托管副本重复执行。

## 服务配置与发布顺序

1. 业务服务：设置 `APP_ENV=production`、PostgreSQL `DATABASE_URL`、`AUTH_MODE=token`、随机 `AUTH_SECRET`、`AGENT_AUDIT_KEY`、受控 `CORS_ORIGINS`。先完成迁移和 `/ready` 检查。
2. 知识服务：设置 `APP_ENV=production`、`LLM_PROVIDER=openai`、服务端模型密钥与地址、`DEVICE_PROVIDER=http`、业务服务地址、`C_IDENTITY_API_BASE_URL`、与业务服务相同的 `AGENT_AUDIT_KEY`，以及持久化 `KNOWLEDGE_STORAGE_PATH`。保持单实例。
3. 在仓库根目录使用拟用于部署的环境变量，分别运行 `python scripts/check_production_config.py business` 和 `python scripts/check_production_config.py knowledge`。该脚本仅检查配置，不代替真实连接测试，也不会被打包进服务容器。
4. 两个 API 均可访问且跨域配置正确后，以公开 API 地址构建前端 `VITE_DATA_MODE=api` 版本，再更新静态托管。不要把 `LLM_API_KEY` 或数据库凭据放入 `VITE_` 变量。
5. 使用授权资料进行上传、检索、诊断、人工确认建单、维修验收与重启后数据保留的端到端验收；确认服务端返回 `is_mock=false`、`is_demo=false`。

ICP备案未完成时，CloudBase 默认域名只用于开发测试。正式使用自定义域名应等待备案完成；默认域名可能显示访问提示页或有访问限制。参见 [CloudBase 默认域名说明](https://docs.cloudbase.net/service/alias)、[CloudBase Run 源码部署](https://docs.cloudbase.net/en/run/deploy/deploy/deploying-source-code) 和 [CFS 挂载说明](https://docs.cloudbase.net/run/deploy/configuring/storage/cfs)。
