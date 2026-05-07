$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".tools\python-3.11.9-embed-amd64\python.exe"

if (-not (Test-Path $Python)) {
    throw "Portable Python is missing. Run the setup steps from README first."
}

$env:PYTHONPATH = $Root
Set-Location $Root
& $Python tests\smoke_flow.py
