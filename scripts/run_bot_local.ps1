$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".tools\python-3.11.9-embed-amd64\python.exe"

if (-not (Test-Path $Python)) {
    throw "Portable Python is missing. Run scripts\setup_local.ps1 first."
}

$env:PYTHONPATH = $Root
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite+aiosqlite:///./.data/eboost.db"
}
if (-not $env:BACKEND_PUBLIC_URL) {
    $env:BACKEND_PUBLIC_URL = "http://localhost:8000"
}
if (-not $env:PAYMENT_PROVIDER) {
    $env:PAYMENT_PROVIDER = "mock"
}
if (-not $env:VPN_PROVIDER) {
    $env:VPN_PROVIDER = "mock"
}

Set-Location $Root
& $Python -m eboost.bot.main
