$ErrorActionPreference = "Stop"
$pidFile = Join-Path (Join-Path (Split-Path -Parent $PSScriptRoot) ".demo-preview") "processes.json"
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Output "未找到本机预览进程记录"; exit 0 }
$ids = (Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json).PSObject.Properties.Value
$all = Get-CimInstance Win32_Process
foreach ($id in $ids) {
    $children = @($all | Where-Object ParentProcessId -eq $id)
    foreach ($child in $children) {
        Get-CimInstance Win32_Process | Where-Object ParentProcessId -eq $child.ProcessId | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
        Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $id -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $pidFile
Write-Output "本机预览进程已停止"
