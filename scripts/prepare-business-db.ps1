param(
    [switch]$SeedDemo
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$businessRoot = Join-Path $projectRoot "services/business"
$businessPython = Join-Path $businessRoot ".venv/Scripts/python.exe"
if ($env:FORGEPILOT_PYTHON) { $businessPython = $env:FORGEPILOT_PYTHON }
if (-not (Test-Path -LiteralPath $businessPython)) { throw "缺少业务服务 Python 环境：$businessPython" }
if (-not $env:DATABASE_URL) { throw "请先在当前终端设置 DATABASE_URL；本脚本不使用默认数据库或示例口令" }
if (-not $env:DATABASE_URL.StartsWith("postgresql")) { throw "本脚本仅用于 PostgreSQL；SQLite 本地演示请使用 start-demo.ps1" }
if ($SeedDemo -and $env:APP_ENV -eq "production") { throw "生产环境禁止写入演示数据" }

Push-Location $businessRoot
try {
    & $businessPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "数据库迁移失败" }
    if ($SeedDemo) {
        & $businessPython -m app.seed
        if ($LASTEXITCODE -ne 0) { throw "演示数据写入失败" }
    }
    & $businessPython -m alembic current
    if ($LASTEXITCODE -ne 0) { throw "无法读取当前迁移版本" }
    Write-Output "数据库准备完成。请启动业务服务并检查 /ready。"
} finally {
    Pop-Location
}
