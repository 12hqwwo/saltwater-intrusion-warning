param(
    [switch]$Full
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Missing .venv\Scripts\python.exe' }

if ($Full) {
    & $python -m unittest discover -s tests -p 'test_*.py'
} else {
    & $python -m unittest tests.test_model_loading tests.test_backend_audit tests.test_security tests.test_spatial_inputs_cache tests.test_dss_storage_errors tests.test_sql_migrations
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& node --test tests/gate_intake_rules.test.mjs tests/river_interpolation.test.mjs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
