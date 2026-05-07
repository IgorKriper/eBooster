$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".tools\python-3.11.9-embed-amd64\python.exe"

function Invoke-Native {
    param(
        [string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $Command $Arguments"
    }
}

if (-not (Test-Path $Python)) {
    throw "Portable Python is missing. Run scripts\setup_local.ps1 first."
}

Set-Location $Root

Write-Output "== compileall =="
Invoke-Native $Python -m compileall eboost tests

Write-Output "== smoke flow =="
Invoke-Native powershell -ExecutionPolicy Bypass -File .\scripts\run_smoke_local.ps1

Write-Output "== provider config smoke =="
Invoke-Native $Python tests\provider_config_smoke.py

Write-Output "== backend mock payment flow =="
Invoke-Native powershell -ExecutionPolicy Bypass -File .\scripts\check_backend_mock_payment_local.ps1

Write-Output "All local checks passed."
