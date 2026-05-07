$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".tools\python-3.11.9-embed-amd64\python.exe"
$DataDir = Join-Path $Root ".data"
$DbFile = Join-Path $DataDir ("backend_flow_" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() + ".db")
$DbUrl = "sqlite+aiosqlite:///" + ($DbFile -replace "\\", "/")
$Port = Get-Random -Minimum 18000 -Maximum 18999
$BaseUrl = "http://127.0.0.1:$Port"

if (-not (Test-Path $Python)) {
    throw "Portable Python is missing. Run scripts\setup_local.ps1 first."
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Set-Location $Root

$env:DATABASE_URL = $DbUrl
$env:BACKEND_PUBLIC_URL = $BaseUrl
$env:BOT_TOKEN = "local-backend-only"
$env:PAYMENT_PROVIDER = "mock"
$env:VPN_PROVIDER = "mock"

$PaymentId = & $Python tests\backend_mock_payment_flow.py
$Job = Start-Job -ScriptBlock {
    param($Root, $DbUrl, $Port)
    Set-Location $Root
    $Python = Join-Path $Root ".tools\python-3.11.9-embed-amd64\python.exe"
    $env:DATABASE_URL = $DbUrl
    $env:BACKEND_PUBLIC_URL = "http://127.0.0.1:$Port"
    $env:BOT_TOKEN = "local-backend-only"
    $env:PAYMENT_PROVIDER = "mock"
    $env:VPN_PROVIDER = "mock"
    & $Python -m uvicorn eboost.backend.main:app --host 127.0.0.1 --port $Port
} -ArgumentList $Root,$DbUrl,$Port

try {
    Start-Sleep -Seconds 7
    $Health = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5 | ConvertTo-Json -Compress
    $Response = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/payments/mock/pay/$PaymentId" -TimeoutSec 5
    & $Python -c "import asyncio; from tests.backend_mock_payment_flow import assert_payment_succeeded; asyncio.run(assert_payment_succeeded(r'$DbUrl', int('$PaymentId'))); print('payment succeeded')"
    Write-Output "PAYMENT_ID=$PaymentId"
    Write-Output "HEALTH=$Health"
    Write-Output "MOCK_PAY_STATUS=$($Response.StatusCode)"
}
finally {
    Stop-Job $Job -ErrorAction SilentlyContinue
    Remove-Job $Job -Force -ErrorAction SilentlyContinue
}
