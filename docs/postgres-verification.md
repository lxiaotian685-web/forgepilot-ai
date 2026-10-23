# PostgreSQL 实测记录（Issue #11）

> 目的：证明迁移、种子数据和测试在真实 PostgreSQL 上可复现，而不是只跑 SQLite。
> 本次使用 PostgreSQL 17.6 本地实例（trust 认证、端口 55432，仅本机测试）。

## 1. 环境

- PostgreSQL 17.6（Windows x64）
- Python 3.14 + `psycopg 3.3.6`
- 数据库：`forgepilot`（演示）、`forgepilot_test`（测试）
- 连接串（本机测试，无口令）：
  `postgresql+psycopg://postgres@127.0.0.1:55432/forgepilot`

## 2. 迁移（空库 → head）

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:55432/forgepilot"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

关键输出：

```text
Running upgrade  -> 0001_initial, initial schema
Running upgrade 0001_initial -> 0002_diagnosis_confirmation, diagnosis confirmation and work order link
Running upgrade 0002_diagnosis_confirmation -> 0003_maintenance_records, maintenance records (device history)
0003_maintenance_records (head)
```

## 3. 种子数据

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:55432/forgepilot"
.\.venv\Scripts\python.exe -m app.seed
```

行数核对：

```text
organizations=2
devices=7
diagnoses=2
work_orders=5
maintenance_records=1
audit_logs=2
```

## 4. 测试（真实 PostgreSQL）

测试库先迁移：

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:55432/forgepilot_test"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

用 `TEST_DATABASE_URL` 跑同一套测试：

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:55432/forgepilot_test"
.\.venv\Scripts\python.exe -m pytest -q
```

输出：

```text
43 passed, 1 warning in 17.72s
```

覆盖：正常确认建单、跨设备拒绝、跨组织拒绝、重复确认幂等、事务失败回滚、刷新后查询、审计查询、鉴权与写入保护、工单完成回写设备历史与去重。

## 5. 迁移回退与重建

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:55432/forgepilot_test"
.\.venv\Scripts\python.exe -m alembic downgrade base
.\.venv\Scripts\python.exe -m alembic upgrade head
```

关键输出：

```text
Running downgrade 0003_maintenance_records -> 0002_diagnosis_confirmation
Running downgrade 0002_diagnosis_confirmation -> 0001_initial
Running downgrade 0001_initial ->
Running upgrade  -> 0001_initial
Running upgrade 0001_initial -> 0002_diagnosis_confirmation
Running upgrade 0002_diagnosis_confirmation -> 0003_maintenance_records
```

## 6. 部署说明

1. 安装 PostgreSQL 并创建空库；数据库账号使用最小权限，不暴露公网。
2. 安装依赖：`pip install -e ".[postgres]"`。
3. 设置 `DATABASE_URL`，执行 `alembic upgrade head`。
4. 仅演示环境执行 `python -m app.seed`；生产不要写演示数据。
5. 回退：`alembic downgrade base`（或指定 revision）。
6. 生产鉴权与写入保护见 `docs/security.md`。

## 7. 说明

- 本记录的端口、trust 认证和路径仅用于本机可复现测试，不代表生产配置。
- 生产必须使用强口令、TLS、最小权限账号，并通过环境变量/密钥管理注入连接串。
