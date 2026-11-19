# Run from the repository: .\run_deploy_tunnel.ps1
# Reads existing .env and cloudflared credentials; never copies secrets into this file.
# run_webgis.py already serves frontend/dist without building. It has no --skip-build flag.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$')]
    [string]$TunnelName = 'dongthap-webgis',
    [uri]$PublicOrigin = 'https://webgis.huutin.xyz',
    [string]$CloudflaredPath,
    [ValidateRange(10, 300)]
    [int]$StartupTimeoutSeconds = 90,
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'run_webgis.py'
$originUrl = 'http://127.0.0.1:8000'
$ownedServer = $null
$ownedTunnel = $null

if ($PublicOrigin.Scheme -ne 'https' -or $PublicOrigin.AbsolutePath -ne '/' -or
    $PublicOrigin.Query -or $PublicOrigin.Fragment -or $PublicOrigin.UserInfo) {
    throw 'PublicOrigin must be an HTTPS origin without a path, query or credentials.'
}
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw 'Missing .venv\Scripts\python.exe. Set up the project environment first.'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\workspace.html') -PathType Leaf)) {
    throw 'Frontend build missing. Run npm.cmd --prefix frontend run build first.'
}
if (-not $CloudflaredPath) {
    $command = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($command) { $CloudflaredPath = $command.Source }
    else {
        $candidates = @(
            (Join-Path $env:ProgramFiles 'cloudflared\cloudflared.exe'),
            (Join-Path ${env:ProgramFiles(x86)} 'cloudflared\cloudflared.exe'),
            (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\cloudflared.exe')
        )
        $CloudflaredPath = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    }
}
if (-not $CloudflaredPath -or -not (Test-Path -LiteralPath $CloudflaredPath -PathType Leaf)) {
    throw 'cloudflared.exe not found. Install Cloudflare.cloudflared or pass -CloudflaredPath.'
}
$CloudflaredPath = (Resolve-Path -LiteralPath $CloudflaredPath).Path

function Test-OriginPort {
    $client = New-Object System.Net.Sockets.TcpClient
    try { return $client.ConnectAsync('127.0.0.1', 8000).Wait(1000) -and $client.Connected }
    catch { return $false }
    finally { $client.Dispose() }
}

function Assert-WebGIS([string]$BaseUrl) {
    $health = Invoke-RestMethod -Uri "$BaseUrl/api/v1/health" -TimeoutSec 10
    $appHealth = Invoke-RestMethod -Uri "$BaseUrl/api/v1/app-health" -TimeoutSec 10
    $page = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/workspace.html" -TimeoutSec 10
    if ($health.status -ne 'ok' -or $health.database_name -ne 'dongthap_gis' -or
        $health.transaction_read_only -ne $true -or $appHealth.status -ne 'ok' -or
        $appHealth.research_mode -ne 'postgres' -or $page.StatusCode -ne 200 -or
        $page.Content -notmatch '(?i)<html') {
        throw 'WebGIS is not a healthy PostgreSQL deployment.'
    }
    $authStatus = 0
    try {
        $authResponse = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/auth/me" -TimeoutSec 10
        $authStatus = [int]$authResponse.StatusCode
    }
    catch {
        if ($null -eq $_.Exception.Response) { throw 'Cannot verify the live login route.' }
        $authStatus = [int]$_.Exception.Response.StatusCode
    }
    if ($authStatus -ne 401) { throw 'Live login protection is not active. Restart WebGIS with current configuration.' }
    # Reject stale server configuration too: these invalid payloads cannot save a record.
    foreach ($probe in @(
        @{ Headers = @{}; Expected = 401 },
        @{ Headers = @{ Origin = 'https://invalid.example'; 'Sec-Fetch-Site' = 'cross-site' }; Expected = 403 }
    )) {
        $status = 0
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/multivariate/history" `
                -Method Post -ContentType 'application/json' -Body '{}' -Headers $probe.Headers -TimeoutSec 10
            $status = [int]$response.StatusCode
        }
        catch {
            if ($null -eq $_.Exception.Response) { throw 'Cannot verify the live write protections.' }
            $status = [int]$_.Exception.Response.StatusCode
        }
        if ($status -ne $probe.Expected) { throw 'Live authentication/origin protection is not active. Restart WebGIS with current configuration.' }
    }
}

function Stop-OwnedProcess($Process) {
    if ($null -ne $Process -and -not $Process.HasExited) {
        # Python's Windows venv launcher can have a child process. Stop only our tree.
        try { & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null }
        catch { Write-Warning "Could not stop owned process $($Process.Id); inspect it manually." }
    }
}

Push-Location -LiteralPath $projectRoot
try {
    $preflight = @'
import os, sys
from run_webgis import load_local_env
try:
    load_local_env()
    from backend.security import enabled
    from backend.database import read_connection
    from urllib.parse import urlsplit
    public = sys.argv[1].rstrip('/')
    hosts = {x.strip() for x in os.getenv('WEBGIS_ALLOWED_HOSTS', '').split(',')}
    origins = {x.strip().rstrip('/') for x in os.getenv('WEBGIS_CORS_ORIGINS', '').split(',')}
    if not enabled() or len(os.getenv('WEBGIS_AUTH_SECRET', '')) < 32 or not os.getenv('WEBGIS_WRITE_API_KEY') or urlsplit(public).hostname not in hosts or '*' in hosts or public not in origins:
        raise ValueError('Security, authentication, allowed host or HTTPS origin configuration is incomplete')
    if os.getenv('WEBGIS_DSS_WRITES_ENABLED', '').lower() == 'true':
        if not all(os.getenv(k) for k in ('DSS_PGUSER', 'WEBGIS_WRITE_API_KEY')):
            raise ValueError('Dedicated writer or write API key is missing')
    with read_connection() as conn:
        row = conn.execute("SELECT current_database() AS db, current_setting('transaction_read_only') AS ro, EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis') AS gis, to_regclass('webgis_security.app_user') IS NOT NULL AS users").fetchone()
        if row['db'] != 'dongthap_gis' or row['ro'] != 'on' or not row['gis'] or not row['users']:
            raise ValueError('Expected dongthap_gis, read-only reader, PostGIS and app_user')
    print('PostgreSQL/PostGIS preflight OK: dongthap_gis; reader read-only; public security configured.')
except Exception as exc:
    print('Preflight failed (' + type(exc).__name__ + '). Check local .env and PostgreSQL; secret values are not displayed.', file=sys.stderr)
    sys.exit(1)
'@
    $preflight | & $pythonPath -B - $PublicOrigin.GetLeftPart([System.UriPartial]::Authority)
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL/security preflight failed. Nothing was started.' }

    $serverAlreadyRunning = Test-OriginPort
    if ($serverAlreadyRunning) {
        Assert-WebGIS $originUrl
        Write-Host 'Reusing healthy PostgreSQL WebGIS on 127.0.0.1:8000; it will not be stopped by this script.'
    }
    if ($CheckOnly) {
        Write-Host 'Preflight passed. No process started (-CheckOnly).'
        return
    }

    $logDirectory = Join-Path $projectRoot ('runs\webgis_evidence\deploy-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + $PID)
    $null = New-Item -ItemType Directory -Path $logDirectory -Force
    if (-not $serverAlreadyRunning) {
        $ownedServer = Start-Process -FilePath $pythonPath -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
            -ArgumentList @('-u', ('"' + $runnerPath + '"'), '--mode', 'postgres', '--host', '127.0.0.1', '--port', '8000') `
            -RedirectStandardOutput (Join-Path $logDirectory 'webgis.stdout.log') `
            -RedirectStandardError (Join-Path $logDirectory 'webgis.stderr.log')
        $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
        $ready = $false
        do {
            if ($ownedServer.HasExited) { throw "WebGIS exited. See logs in $logDirectory" }
            try { Assert-WebGIS $originUrl; $ready = $true }
            catch { Start-Sleep -Seconds 1 }
        } until ($ready -or (Get-Date) -ge $deadline)
        if (-not $ready) { throw "WebGIS startup timed out. See logs in $logDirectory" }
    }

    $ownedTunnel = Start-Process -FilePath $CloudflaredPath -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -ArgumentList @('tunnel', '--url', $originUrl, 'run', $TunnelName) `
        -RedirectStandardOutput (Join-Path $logDirectory 'tunnel.stdout.log') `
        -RedirectStandardError (Join-Path $logDirectory 'tunnel.stderr.log')
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $publicReady = $false
    do {
        if ($ownedTunnel.HasExited) { throw "Tunnel exited. Check existing cloudflared login/credentials. Logs: $logDirectory" }
        try { Assert-WebGIS $PublicOrigin.GetLeftPart([System.UriPartial]::Authority); $publicReady = $true }
        catch { Start-Sleep -Seconds 2 }
    } until ($publicReady -or (Get-Date) -ge $deadline)
    if (-not $publicReady) { throw "Public checks timed out. Check tunnel DNS/route and logs: $logDirectory" }

    Write-Host "READY: $($PublicOrigin.GetLeftPart([System.UriPartial]::Authority))/workspace.html" -ForegroundColor Green
    Write-Host 'Local/public workspace, health and app-health passed in postgres mode.'
    Write-Host "Logs (Git-ignored): $logDirectory"
    Write-Host 'Keep this terminal running. Ctrl+C stops only the processes started by this script.'
    while (-not $ownedTunnel.HasExited) {
        if ($null -ne $ownedServer -and $ownedServer.HasExited) { throw 'WebGIS stopped; closing its tunnel.' }
        Start-Sleep -Seconds 2
    }
    throw "Tunnel stopped (exit $($ownedTunnel.ExitCode)). See $logDirectory"
}
finally {
    Stop-OwnedProcess $ownedTunnel
    Stop-OwnedProcess $ownedServer
    Pop-Location
}
