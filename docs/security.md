# 认证与公开写入保护方案

> 适用：Issue #11 ｜ 分支 `task/b-diagnosis-persistence`
> 结论：当前 `demo` 模式只用于本地/评审；生产必须切换到 `token` 模式并叠加写入保护。

## 1. 当前 v0.1 演示认证（仅本地/评审）

- 请求头 `X-Organization-Id`、`X-User-Id` 指定组织与用户；不传时回退 `demo-org` / `demo@example.com`。
- 优点：Swagger/curl 可直接调试。
- 风险：**客户端可任意伪造组织和用户**；默认身份会掩盖未认证访问。禁止用于公网生产。

## 2. 登录与 Bearer 令牌

已实现（`app/api/auth.py`、`app/auth.py`、`app/security.py`）：

- `POST /api/v1/auth/login`：邮箱 + 密码 + 可选 `organizationCode`，校验通过后签发令牌。
- 密码使用 PBKDF2-HMAC-SHA256（每用户随机盐，默认 120000 次迭代）存储，禁止明文。
- 令牌为 HMAC-SHA256 签名，载荷包含 `org`、`user`、`exp`；有效期由 `AUTH_TOKEN_TTL_SECONDS` 控制（默认 3600 秒）。
- `AUTH_MODE=token` 时只接受 `Authorization: Bearer <token>`，忽略 `X-Organization-Id` / `X-User-Id`。
- `AUTH_MODE=demo` 时优先使用 Bearer 令牌；没有令牌才回退演示请求头。登录接口本身豁免 `WRITE_API_KEY`。
- `AUTH_SECRET` 未配置时拒绝签发/校验；服务端仍会校验组织、用户和成员关系。
- 登录成功写入 `auth.login` 审计。

演示账号（仅本地/评审）：`demo@example.com` / `ForgePilot123!`，其他演示用户同密码，角色不同。
**生产必须替换演示密码，并增加密码策略、失败锁定、找回/重置流程。**

命令行也可直接签发评审令牌：

```powershell
$env:AUTH_SECRET="至少32位随机字符串"
.\.venv\Scripts\python.exe -m app.auth demo-org demo@example.com
```

调用：

```powershell
curl.exe -H "Authorization: Bearer <token>" http://127.0.0.1:8000/api/v1/diagnoses
```

**定位**：登录 + HMAC 令牌是评审演示的过渡认证，不是完整登录体系。正式上线应替换为 OIDC/JWT/会话，支持吊销、刷新和审计。

## 3. 公开写入保护

1. `WRITE_API_KEY`（已实现）
   - 设置后，所有 `POST/PUT/PATCH/DELETE /api/v1/*` 必须携带 `X-Write-Key`，否则 403。
   - 与 `AUTH_MODE=token` 叠加使用，形成“身份 + 写入凭证”双闸门。
2. 限流
   - 在 Nginx/API 网关按 IP + 路径限流，写接口建议 10 次/分钟；登录/令牌接口单独更严格。
3. CORS
   - `CORS_ORIGINS` 只保留本地和正式前端域名，禁止 `*`；不要与 `allow_credentials=True` 搭配通配来源。
4. 关闭调试面
   - 生产设置 `DOCS_ENABLED=false`，关闭 `/docs`、`/redoc`、`/openapi.json`。
5. 传输与数据
   - 全站 HTTPS；PostgreSQL 不暴露公网；数据库账号最小权限；口令只放环境变量/密钥管理，不提交仓库。
6. 审计
   - 所有写操作在事务内写 `audit_logs`；审计查询仅 `manager+` 可访问，按组织隔离。

## 4. 生产配置示例

```dotenv
DATABASE_URL=postgresql+psycopg://forgepilot:********@db:5432/forgepilot
AUTH_MODE=token
AUTH_SECRET=<32+位随机值>
WRITE_API_KEY=<独立随机值>
DOCS_ENABLED=false
CORS_ORIGINS=https://forgepilot.example.com
```

## 5. 验收与残余风险

- 验收：无令牌/伪造头访问写接口 → 401/403；缺少 `X-Write-Key` → 403；跨组织查询 → 404。
- 残余风险：当前 token 模式无吊销列表、无刷新机制、无双因素；登录暂无失败锁定、找回密码和密码策略；正式上线前必须替换为完整登录体系并做安全评审。
