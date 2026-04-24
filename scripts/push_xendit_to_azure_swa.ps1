# Push Xendit-related app settings from api/local.settings.json to Azure Static Web Apps (API).
# Usage: .\scripts\push_xendit_to_azure_swa.ps1
# Prereq: az login, subscription with SWA "swa-lexmateph-us" in RG "LexMatePH"
# Sets XENDIT_BYPASS to false in Azure (live mode) regardless of local file.

$ErrorActionPreference = "Stop"
# This script lives in <repo>/scripts
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path (Join-Path $root "api\local.settings.json"))) {
  throw "api/local.settings.json not found (expected under $root)"
}

$j = Get-Content "$root\api\local.settings.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$v = $j.Values
$apiKey = [string]$v.XENDIT_API_KEY
$wh = [string]$v.XENDIT_WEBHOOK_TOKEN
$fe = if ($v.FRONTEND_URL) { [string]$v.FRONTEND_URL } else { "https://lexmateph.com" }
if ([string]::IsNullOrWhiteSpace($apiKey) -or [string]::IsNullOrWhiteSpace($wh)) {
  throw "XENDIT_API_KEY and XENDIT_WEBHOOK_TOKEN must be set in api/local.settings.json"
}

# Azure Static Web App where the Python API is hosted (see .github workflow / ADR 001)
$swaName = "swa-lexmateph-us"
$rg = "LexMatePH"

# az accepts multiple key=value; avoid printing secrets
Write-Host "Pushing XENDIT_API_KEY, XENDIT_WEBHOOK_TOKEN, XENDIT_BYPASS=false, FRONTEND_URL to $swaName / $rg ..."
& az staticwebapp appsettings set -n $swaName -g $rg @(
  "--setting-names"
  "XENDIT_API_KEY=$apiKey"
  "XENDIT_WEBHOOK_TOKEN=$wh"
  "XENDIT_BYPASS=false"
  "FRONTEND_URL=$fe"
)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done. (XENDIT_BYPASS is false in Azure; local file unchanged.)"
