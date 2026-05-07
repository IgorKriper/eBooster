$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".tools\python-3.11.9-embed-amd64\python.exe"
$DataDir = Join-Path $Root ".data"

if (-not (Test-Path $Python)) {
    throw "Portable Python is missing. Run the setup steps from README first."
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

$env:PYTHONPATH = $Root
$env:BOT_TOKEN = "local-backend-only"
$env:DATABASE_URL = "sqlite+aiosqlite:///./.data/eboost.db"
$env:BACKEND_PUBLIC_URL = "http://localhost:8000"
$env:PAYMENT_PROVIDER = "mock"
$env:VPN_PROVIDER = "mock"

Set-Location $Root
& $Python -m uvicorn eboost.backend.main:app --host 127.0.0.1 --port 8000
