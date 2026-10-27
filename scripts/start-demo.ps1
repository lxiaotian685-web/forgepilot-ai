param(
    [int]$FrontendPort = 5180,
    [int]$BusinessPort = 8001,
    [int]$KnowledgePort = 8002
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$businessRoot = Join-Path $projectRoot "services/business"
$knowledgeRoot = Join-Path $projectRoot "services/knowledge"
$frontendRoot = Join-Path $projectRoot "frontend"
$businessPython = Join-Path $businessRoot ".venv/Scripts/python.exe"
$knowledgePython = Join-Path $knowledgeRoot ".venv/Scripts/python.exe"
if ($env:FORGEPILOT_PYTHON) {
    $businessPython = $env:FORGEPILOT_PYTHON
    $knowledgePython = $env:FORGEPILOT_PYTHON
}
$logRoot = Join-Path $projectRoot ".demo-preview"
$pidFile = Join-Path $logRoot "processes.json"
$previewDb = "sqlite+pysqlite:///./forgepilot-demo.db"

if (-not (Test-Path -LiteralPath $businessPython)) { throw "缺少业务服务虚拟环境：$businessPython" }
if (-not (Test-Path -LiteralPath $knowledgePython)) { throw "缺少知识服务虚拟环境：$knowledgePython" }
if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "node_modules"))) { throw "缺少前端依赖，请在 frontend 目录执行 npm ci" }
foreach ($port in @($FrontendPort, $BusinessPort, $KnowledgePort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "端口 $port 已被占用" }
}
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $businessRoot "forgepilot-demo.db"))) {
    $oldDatabaseUrl = $env:DATABASE_URL
    try {
        $env:DATABASE_URL = $previewDb
        Push-Location $businessRoot
        try { & $businessPython -m app.seed | Out-Null; if ($LASTEXITCODE -ne 0) { throw "演示数据库初始化失败" } }
        finally { Pop-Location }
    } finally { $env:DATABASE_URL = $oldDatabaseUrl }
}

$previewSecret = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$origin = "http://127.0.0.1:$FrontendPort"
$businessUrl = "http://127.0.0.1:$BusinessPort"
$knowledgeUrl = "http://127.0.0.1:$KnowledgePort"
$started = @()
try {
    $business = Start-Process -FilePath $businessPython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BusinessPort") -WorkingDirectory $businessRoot -Environment @{
        DATABASE_URL = $previewDb
        AUTH_MODE = "token"
        AUTH_SECRET = $previewSecret
        AUTH_TOKEN_TTL_SECONDS = "43200"
        CORS_ORIGINS = $origin
    } -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot "business.out.log") -RedirectStandardError (Join-Path $logRoot "business.err.log")
    $started += $business
    $knowledge = Start-Process -FilePath $knowledgePython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$KnowledgePort") -WorkingDirectory $knowledgeRoot -Environment @{
        C_REQUIRE_AUTH = "true"
        C_IDENTITY_API_BASE_URL = $businessUrl
        C_ENABLE_INGEST = "true"
        DEVICE_PROVIDER = "http"
        DEVICE_API_BASE_URL = $businessUrl
        CORS_ORIGINS = $origin
    } -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot "knowledge.out.log") -RedirectStandardError (Join-Path $logRoot "knowledge.err.log")
    $started += $knowledge
    $frontend = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort") -WorkingDirectory $frontendRoot -Environment @{
        VITE_DATA_MODE = "api"
        VITE_API_BASE_URL = $businessUrl
        VITE_BUSINESS_API_BASE_URL = $businessUrl
        VITE_DIAGNOSIS_API_BASE_URL = $knowledgeUrl
    } -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot "frontend.out.log") -RedirectStandardError (Join-Path $logRoot "frontend.err.log")
    $started += $frontend
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $businessHealth = (Invoke-WebRequest "$businessUrl/health" -UseBasicParsing -TimeoutSec 2).StatusCode
            $knowledgeHealth = (Invoke-WebRequest "$knowledgeUrl/health" -UseBasicParsing -TimeoutSec 2).StatusCode
            $frontendHealth = (Invoke-WebRequest "$origin/forgepilot/" -UseBasicParsing -TimeoutSec 2).StatusCode
            if ($businessHealth -eq 200 -and $knowledgeHealth -eq 200 -and $frontendHealth -eq 200) { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) { throw "预览服务未在 15 秒内全部就绪，请检查 $logRoot 的日志" }
    @{ business = $business.Id; knowledge = $knowledge.Id; frontend = $frontend.Id } | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding utf8
    Write-Output "预览地址：$origin/forgepilot/"
    Write-Output "演示账号：demo@example.com / ForgePilot123!"
    Write-Output "停止命令：& '$PSScriptRoot/stop-demo.ps1'"
} catch {
    foreach ($process in $started) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    throw
}
