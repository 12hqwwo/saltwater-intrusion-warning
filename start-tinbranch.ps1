# Serve the latest TinBranch code and new frontend with existing PostgreSQL settings.
[CmdletBinding()]
param(
    [string]$SettingsRoot = 'D:\Study\TLCN',
    [ValidateSet('postgres', 'snapshot')]
    [string]$Mode = 'postgres',
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$frontendRoot = Join-Path $projectRoot 'frontend'
$frontendDist = Join-Path $frontendRoot 'dist'
$pythonPath = Join-Path $SettingsRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $SettingsRoot '.venv-api\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Không tìm thấy môi trường Python tại $SettingsRoot."
}
if (-not $SkipBuild) {
    & npm.cmd --prefix $frontendRoot run build
    if ($LASTEXITCODE -ne 0) { throw 'Không dựng được giao diện mới.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendDist 'workspace.html'))) {
    throw 'Chưa có bản dựng giao diện mới.'
}

$serverCode = @'
import os
import sys
from pathlib import Path

project_root = Path(sys.argv[1]).resolve()
settings_root = Path(sys.argv[2]).resolve()
frontend_dist = Path(sys.argv[3]).resolve()
mode = sys.argv[4]
port = int(sys.argv[5])
os.chdir(project_root)
sys.path.insert(0, str(project_root))
import run_webgis
run_webgis.ROOT = settings_root
run_webgis.load_local_env()
run_webgis.ROOT = project_root
os.environ['WEBGIS_RESEARCH_MODE'] = mode
os.environ['WEBGIS_RESEARCH_FILE'] = str(project_root / 'data/research/workspace.json')
from backend.security import enabled
if not enabled():
    raise SystemExit('Chưa bật bảo vệ API trong dự án backend.')
if mode == 'postgres':
    from backend.database import read_connection
    with read_connection() as connection:
        connection.execute('SELECT 1')
from backend.main import app
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn

app.add_api_route('/', lambda: RedirectResponse('/workspace.html'), methods=['GET'])
app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='webgis')
uvicorn.run(app, host='127.0.0.1', port=port)
'@

Write-Host "Giao diện mới: http://127.0.0.1:$Port/workspace.html#overview"
Write-Host "Backend TinBranch · thiết lập PostgreSQL: $SettingsRoot · chế độ $Mode"
& $pythonPath -B -c $serverCode $projectRoot $SettingsRoot $frontendDist $Mode $Port
if ($LASTEXITCODE -ne 0) { throw "WebGIS dừng với mã $LASTEXITCODE." }
