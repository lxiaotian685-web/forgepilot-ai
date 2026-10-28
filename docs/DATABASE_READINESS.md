# 业务数据库准备与验证

当前公网预览只托管静态前端，尚未部署业务 API 或 PostgreSQL。本说明用于独立准备 B 服务数据库，不代表公网数据库已经上线。

## PostgreSQL 路径

先创建空数据库与最小权限账号，安装 `services/business` 的 `.[postgres]` 依赖。连接串应由部署平台的密钥配置注入，不能提交到仓库。Windows PowerShell 示例：

```powershell
$env:APP_ENV = "production"
$env:DATABASE_URL = "postgresql+psycopg://<user>:<password>@<db-host>:5432/<database>"
& .\scripts\prepare-business-db.ps1
```

脚本要求显式 `DATABASE_URL`，只接受 PostgreSQL，执行 `alembic upgrade head` 并输出当前版本。仅开发演示环境可用 `-SeedDemo` 加载虚构账号；生产环境会拒绝该选项。迁移前应先备份现有数据库，不能对已有业务库执行清空操作。

业务服务启动后分别检查：

```text
GET /health  检查应用进程是否存活
GET /ready   执行 SELECT 1，数据库不可用时返回 503
```

生产环境须同时配置 `AUTH_MODE=token`、随机 `AUTH_SECRET`、受控 `CORS_ORIGINS` 和 HTTPS 入口。`APP_ENV=production` 会拒绝 SQLite 连接；不要使用 `.env.example` 中的示例口令。

## 本地演示路径

`scripts/start-demo.ps1` 使用独立 SQLite 文件和虚构种子数据。SQLite 演示以 SQLAlchemy 元数据建表，不使用 PostgreSQL 专用的 Alembic 迁移。不要把该脚本原样用于公开部署。

自动化测试验证：演示组织、设备与工单写入文件数据库后，新建数据库连接仍可查询；`/ready` 必须实际执行数据库查询，故障时返回 503。真实 PostgreSQL 的迁移和测试已有 [本地实测记录](../services/business/docs/postgres-verification.md)，部署到新的数据库时还需按本节重新执行与验收。
