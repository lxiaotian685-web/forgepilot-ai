# Linux/macOS 本地运行

以下命令仅用于 127.0.0.1 上的虚构演示环境。三个服务必须分别从各自目录启动，因为 B/C 都有独立的 `app` Python 包。需要 Python 3.10+、Node.js 20+、npm。

先安装依赖：

```bash
cd services/business
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cd ../knowledge
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cd ../../frontend
npm ci
```

终端 1，启动 B 业务服务并初始化虚构数据库：

```bash
cd services/business
export DATABASE_URL='sqlite+pysqlite:///./forgepilot-demo.db'
export AUTH_MODE=token
export AUTH_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export CORS_ORIGINS='http://127.0.0.1:5180'
.venv/bin/python -m app.seed
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

终端 2，启动 C 知识诊断服务：

```bash
cd services/knowledge
export C_IDENTITY_API_BASE_URL='http://127.0.0.1:8001'
export DEVICE_PROVIDER=http
export DEVICE_API_BASE_URL='http://127.0.0.1:8001'
export C_ENABLE_INGEST=true
export CORS_ORIGINS='http://127.0.0.1:5180'
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

终端 3，启动前端 API 模式：

```bash
cd frontend
export VITE_DATA_MODE=api
export VITE_API_BASE_URL='http://127.0.0.1:8001'
export VITE_BUSINESS_API_BASE_URL='http://127.0.0.1:8001'
export VITE_DIAGNOSIS_API_BASE_URL='http://127.0.0.1:8002'
npm run dev -- --host 127.0.0.1 --port 5180 --strictPort
```

打开 `http://127.0.0.1:5180/forgepilot/`。演示账号 `demo@example.com` / `ForgePilot123!`，只适用于本机虚构数据。当前未配置真实模型密钥，诊断明确标记为 mock，不允许作为正式诊断保存。停止各终端用 `Ctrl+C`。
