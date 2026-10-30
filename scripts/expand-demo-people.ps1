$ErrorActionPreference = 'Stop'
# Only the loopback demo instance is targeted; reruns skip existing members.
$base = 'http://127.0.0.1:8001'
$login = Invoke-RestMethod -Method Post -Uri "$base/api/v1/auth/login" -ContentType 'application/json' -Body '{"email":"demo@example.com","password":"ForgePilot123!"}'
if ($login.organization.code -ne 'demo-org') { throw '不是演示组织，已停止' }
$headers = @{ Authorization = "Bearer $($login.accessToken)" }
$members = Invoke-RestMethod -Uri "$base/api/v1/members?pageSize=100" -Headers $headers
$examples = @(@('chen','陈敏','admin'), @('liu','刘海','manager'), @('zhou','周宁','technician'), @('huang','黄伟','technician'), @('lin','林悦','technician'), @('sun','孙晓','viewer'), @('wu','吴峰','technician'))
foreach ($person in $examples) {
    $email = "demo-$($person[0])@example.com"
    if ($members.items.email -contains $email) { continue }
    $body = @{email=$email;displayName=$person[1];role=$person[2];initialPassword=[guid]::NewGuid().ToString('N')} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$base/api/v1/members" -Headers $headers -ContentType 'application/json' -Body $body | Out-Null
    Write-Output "已补充演示人员：$($person[1])"
}
