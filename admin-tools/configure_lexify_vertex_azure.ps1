#requires -Version 5.1
<#
.SYNOPSIS
  Push Lexify / Vertex AI app settings to an Azure Static Web App (managed API) via Azure CLI.

.DESCRIPTION
  Uses `az rest` to PUT Microsoft.Web/staticSites/.../config/appsettings so large
  GOOGLE_SERVICE_ACCOUNT_JSON values are handled safely (not shell-escaped).

  **Merges** with existing app settings (GET then overlay Vertex keys). A bare PUT
  replaces all settings and would remove DB_CONNECTION_STRING — this script avoids that.

  Prereqs:
    - Azure CLI (`az`) installed and `az login` done
    - Google Cloud: service account JSON key file (Vertex AI User on your GCP project)
    - Static Web App on Standard plan may be required for some app-setting APIs (see Azure docs)

.PARAMETER ResourceGroup
  Azure resource group that contains the Static Web App.

.PARAMETER StaticWebAppName
  Name of the Static Web App resource (default matches api/host.json hostname prefix).

.PARAMETER ServiceAccountJsonPath
  Full path to the downloaded GCP service account .json key (never commit this file).

.PARAMETER GoogleCloudProject
  GCP project id (must match the service account's project).

.PARAMETER DryRun
  Only write the ARM request body to a temp file and print the `az rest` command; do not call Azure.

.EXAMPLE
  .\admin-tools\configure_lexify_vertex_azure.ps1 `
    -ResourceGroup "my-rg" `
    -ServiceAccountJsonPath "C:\secrets\lexmate-vertex-sa.json"

.EXAMPLE
  az login
  az account set --subscription "YOUR-SUBSCRIPTION-ID-OR-NAME"
  .\admin-tools\configure_lexify_vertex_azure.ps1 -ResourceGroup "my-rg" -ServiceAccountJsonPath ".\sa.json"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ResourceGroup,

    [Parameter(Mandatory = $false)]
    [string] $StaticWebAppName = "swa-lexmateph-us",

    [Parameter(Mandatory = $true)]
    [string] $ServiceAccountJsonPath,

    [Parameter(Mandatory = $false)]
    [string] $GoogleCloudProject = "gen-lang-client-0565960161",

    [switch] $DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI (az) not found. Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
}

$resolvedSa = Resolve-Path -LiteralPath $ServiceAccountJsonPath
$rawSa = [System.IO.File]::ReadAllText($resolvedSa.Path)

# Validate JSON so we fail fast before touching Azure
try {
    $null = $rawSa | ConvertFrom-Json
} catch {
    Write-Error "Service account file is not valid JSON: $($_.Exception.Message)"
}

$disallowed = @("AzureWebJobsStorage", "FUNCTIONS_WORKER_RUNTIME")
$existing = az staticwebapp appsettings list --name $StaticWebAppName --resource-group $ResourceGroup -o json 2>$null | ConvertFrom-Json
$merged = [ordered]@{}
if ($existing -and $existing.properties) {
    foreach ($p in $existing.properties.PSObject.Properties) {
        if ($disallowed -contains $p.Name) { continue }
        $merged[$p.Name] = "$($p.Value)"
    }
}
$merged["GOOGLE_CLOUD_PROJECT"]       = $GoogleCloudProject
$merged["GOOGLE_CLOUD_LOCATION"]      = "global"
$merged["GEMINI_VERTEX_MODEL"]        = "gemini-3-flash-preview"
$merged["GOOGLE_SERVICE_ACCOUNT_JSON"] = $rawSa

$bodyObj = @{ properties = $merged }
# Depth must be high enough for the nested JSON string
$bodyJson = $bodyObj | ConvertTo-Json -Depth 20 -Compress:$false

$tmp = [System.IO.Path]::GetTempFileName() + ".json"
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($tmp, $bodyJson, $utf8NoBom)
} catch {
    Write-Error "Failed to write temp body: $($_.Exception.Message)"
}

$subId = az account show --query id -o tsv 2>$null
if (-not $subId) {
    Write-Error "Not logged in. Run: az login`nThen: az account set --subscription <id-or-name>"
}

$apiVersion = "2022-03-01"
$uri = "https://management.azure.com/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/staticSites/$StaticWebAppName/config/appsettings?api-version=$apiVersion"

Write-Host "Subscription: $subId"
Write-Host "Resource:     $StaticWebAppName (rg: $ResourceGroup)"
Write-Host "Body file:    $tmp"
Write-Host "GCP project:  $GoogleCloudProject"

if ($DryRun) {
    Write-Host "`nDry run - run this manually:" -ForegroundColor Yellow
    Write-Host "az rest --method PUT --uri `"$uri`" --body `"@$tmp`" --headers `"Content-Type=application/json`""
    exit 0
}

Write-Host "`nApplying app settings via Azure REST..." -ForegroundColor Cyan
az rest --method PUT --uri $uri --body "@$tmp" --headers "Content-Type=application/json" -o none
if ($LASTEXITCODE -ne 0) {
    Write-Error "az rest failed (exit $LASTEXITCODE). If you see permission or SKU errors, use the Portal or upgrade the Static Web App plan."
}

Write-Host "`nDone. Verify with:" -ForegroundColor Green
Write-Host "  az staticwebapp appsettings list --name $StaticWebAppName --resource-group $ResourceGroup -o table"
Write-Host "`nWait a minute for the API to restart, then test Lexify grading."
