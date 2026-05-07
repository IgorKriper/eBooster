$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ToolsDir = Join-Path $Root ".tools"
$PythonZip = Join-Path $ToolsDir "python-3.11.9-embed-amd64.zip"
$PythonDir = Join-Path $ToolsDir "python-3.11.9-embed-amd64"
$Python = Join-Path $PythonDir "python.exe"
$GetPip = Join-Path $ToolsDir "get-pip.py"
$Pth = Join-Path $PythonDir "python311._pth"

New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null

if (-not (Test-Path $PythonZip)) {
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -OutFile $PythonZip
}

if (-not (Test-Path $Python)) {
    Expand-Archive -Path $PythonZip -DestinationPath $PythonDir
}

$PthContent = Get-Content $Pth
$PthContent = $PthContent -replace "#import site", "import site"
if ($PthContent -notcontains $Root) {
    $PthContent += $Root
}
$PthContent | Set-Content $Pth

if (-not (Test-Path $GetPip)) {
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip
}

& $Python $GetPip --no-warn-script-location
& $Python -m pip install --no-warn-script-location -r (Join-Path $Root "requirements-dev.txt")
& $Python --version
