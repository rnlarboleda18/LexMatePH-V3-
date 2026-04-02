# LexMatePH v3 — stop dev processes and relaunch via start_all.ps1
$here = $PSScriptRoot
if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }

Write-Host "=========================================="
Write-Host "   LexMatePH v3 - Restart"
Write-Host "=========================================="
Write-Host ""

Write-Host "[INFO] Stopping node / func hosts..."
Get-Process | Where-Object { $_.ProcessName -like "*node*" -or $_.ProcessName -like "*func*" } | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

$startAll = Join-Path $here "start_all.ps1"
Write-Host "[INFO] Relaunching: $startAll"
& $startAll
