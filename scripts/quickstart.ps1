param(
    [switch]$InstallOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command Start-Process).Parameters.ContainsKey('Environment')) {
    throw '请使用 PowerShell 7.4 或更高版本运行本地演示。'
}

function Assert-Command($name, $minimumMajor) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $command) { throw "未找到 $name。请先安装 $name（主版本至少 $minimumMajor）。" }
    $versionText = & $name --version
    if ($LASTEXITCODE -ne 0) { throw "无法读取 $name 的版本。" }
    $match = [regex]::Match("$versionText", '(\d+)\.')
    if (-not $match.Success -or [int]$match.Groups[1].Value -lt $minimumMajor) {
        throw "$name 版本过低：$versionText。需要主版本至少 $minimumMajor。"
    }
}

Assert-Command python 3
Assert-Command node 20
Assert-Command npm.cmd 1
$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pythonVersion -lt [version]'3.10') { throw "Python 版本过低：$pythonVersion。需要 3.10 或更高版本。" }

foreach ($service in @('business', 'knowledge')) {
    $serviceRoot = Join-Path $projectRoot "services/$service"
    $pythonPath = Join-Path $serviceRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        & python -m venv (Join-Path $serviceRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw "$service 虚拟环境创建失败。" }
    }
    Push-Location $serviceRoot
    try {
        & $pythonPath -m pip install -e .
        if ($LASTEXITCODE -ne 0) { throw "$service 依赖安装失败。" }
    } finally { Pop-Location }
}

$frontendRoot = Join-Path $projectRoot 'frontend'
Push-Location $frontendRoot
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败。' }
} finally { Pop-Location }

if (-not $InstallOnly) { & (Join-Path $PSScriptRoot 'start-demo.ps1') }
