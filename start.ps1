# start.ps1 — Khoi dong Backend + Frontend cung luc
# Chay: .\start.ps1

[CmdletBinding()]
param(
    [ValidateSet('snapshot', 'postgres')]
    [string]$Mode = 'postgres',
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $projectRoot '.venv-api\Scripts\python.exe'
}
$frontendPath = Join-Path $projectRoot 'frontend'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Python environment missing. Follow docs/run_guide.md to set up .venv or .venv-api.'
}

if (-not $SkipBuild) {
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'Node.js/npm is required to build the frontend.'
    }
    & npm.cmd --prefix $frontendPath run build
    if ($LASTEXITCODE -ne 0) {
        throw 'Frontend build failed. The server was not started.'
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendPath 'dist\workspace.html'))) {
    throw 'Frontend build missing. Run .\start.ps1 without -SkipBuild.'
}

Write-Host "Starting WebGIS ($Mode). Wait for Uvicorn startup confirmation." -ForegroundColor Cyan
Write-Host "Workspace: http://127.0.0.1:$Port/workspace.html"
Write-Host "API docs:  http://127.0.0.1:$Port/docs"
Write-Host 'Press Ctrl+C in this terminal to stop.'

& $pythonPath (Join-Path $projectRoot 'run_webgis.py') --mode $Mode --port $Port
if ($LASTEXITCODE -ne 0) {
    throw "WebGIS stopped with exit code $LASTEXITCODE."
}
