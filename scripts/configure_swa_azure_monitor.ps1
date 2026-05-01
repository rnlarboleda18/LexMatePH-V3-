<#
.SYNOPSIS
  Configure an Azure Static Web App (managed Python API) for Admin Monitor: app settings + managed identity + Reader RBAC via Azure CLI.

.DESCRIPTION
  Sets AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP on the SWA so /api/ops/azure-metrics works in production (no local az CLI).
  Enables system-assigned managed identity and grants Reader on the resource group that holds Postgres / monitored resources.
  Optional: Cost Management Reader at subscription scope for the cost panel in Monitor.

.PARAMETER StaticWebAppName
  Name of the Static Web App resource in Azure.

.PARAMETER StaticWebAppResourceGroup
  Resource group containing the Static Web App.

.PARAMETER MonitorResourceGroup
  Resource group where PostgreSQL Flexible Server and other monitored resources live (defaults to StaticWebAppResourceGroup).

.PARAMETER SubscriptionId
  Azure subscription GUID. If omitted, uses the current default from `az account show`.

.PARAMETER PostgresServerName
  If set, adds AZURE_POSTGRES_SERVER_NAME (avoids wrong ARM list-first pick).

.PARAMETER FunctionAppSiteName
  If set, adds AZURE_FUNCTION_APP_NAME (underlying Functions site name when not using ARM discovery).

.PARAMETER StaticWebAppResourceNameForMetrics
  If set, adds AZURE_STATIC_WEB_APP_NAME when it differs from discovery (usually same as StaticWebAppName).

.PARAMETER SkipManagedIdentity
  Only apply app settings; do not change identity or role assignments.

.PARAMETER AssignCostManagementReader
  Also grant Cost Management Reader at subscription scope (helps the cost query in Monitor).

.NOTES
  Requires: az CLI, logged-in account with permission to modify the SWA and create role assignments.
  Does not set AZURE_CLIENT_* (service principal); prefer managed identity as implemented in api/blueprints/admin.py.

.EXAMPLE
  ./configure_swa_azure_monitor.ps1 -StaticWebAppName "my-swa" -StaticWebAppResourceGroup "LexMatePH"

.EXAMPLE
  ./configure_swa_azure_monitor.ps1 -StaticWebAppName "my-swa" -StaticWebAppResourceGroup "RG-SWA" -MonitorResourceGroup "LexMatePH" -PostgresServerName "my-pg" -AssignCostManagementReader
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string] $StaticWebAppName,

    [Parameter(Mandatory = $true)]
    [string] $StaticWebAppResourceGroup,

    [string] $MonitorResourceGroup = "",

    [string] $SubscriptionId = "",

    [string] $PostgresServerName = "",

    [string] $FunctionAppSiteName = "",

    [string] $StaticWebAppResourceNameForMetrics = "",

    [switch] $SkipManagedIdentity,

    [switch] $AssignCostManagementReader
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-AzCommand([string[]] $Arguments) {
    Write-Host ("> az " + ($Arguments -join " "))
}

function Invoke-AzNative {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )
    # Azure CLI writes progress to stderr; with $ErrorActionPreference = Stop that can terminate the script.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & az @Arguments
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

function Invoke-Az {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )
    Write-AzCommand $Arguments
    $null = Invoke-AzNative -Arguments $Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "az failed with exit code $LASTEXITCODE"
    }
}

function Get-AzText {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )
    Write-AzCommand $Arguments
    $out = (Invoke-AzNative -Arguments $Arguments | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "az failed with exit code $LASTEXITCODE"
    }
    return $out
}

function Get-SwaPrincipalId {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $ResourceGroup,
        [Parameter(Mandatory = $true)][string] $Subscription
    )
    $azArgs = @(
        "staticwebapp", "identity", "show",
        "-n", $Name,
        "-g", $ResourceGroup,
        "--subscription", $Subscription,
        "--query", "principalId",
        "-o", "tsv"
    )
    Write-AzCommand $azArgs
    $raw = Invoke-AzNative -Arguments $azArgs
    if ($LASTEXITCODE -ne 0) {
        return ""
    }
    return ($raw | Out-String).Trim()
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI (az) not found. Install from https://aka.ms/installazurecliwindows"
}

if (-not $MonitorResourceGroup) {
    $MonitorResourceGroup = $StaticWebAppResourceGroup
}

if (-not $SubscriptionId) {
    $SubscriptionId = Get-AzText -Arguments @("account", "show", "--query", "id", "-o", "tsv")
    if (-not $SubscriptionId) {
        throw "Could not resolve subscription id. Run: az account set --subscription <id>"
    }
}

$monitorScope = "/subscriptions/$SubscriptionId/resourceGroups/$MonitorResourceGroup"

Write-Host "Subscription: $SubscriptionId"
Write-Host "SWA RG:       $StaticWebAppResourceGroup"
Write-Host "Monitor RG:   $MonitorResourceGroup (Reader scope)"
Write-Host ""

# --- App settings (SWA API environment) ---
$settings = @(
    "AZURE_SUBSCRIPTION_ID=$SubscriptionId",
    "AZURE_RESOURCE_GROUP=$MonitorResourceGroup"
)
if ($PostgresServerName) {
    $settings += "AZURE_POSTGRES_SERVER_NAME=$PostgresServerName"
}
if ($FunctionAppSiteName) {
    $settings += "AZURE_FUNCTION_APP_NAME=$FunctionAppSiteName"
}
if ($StaticWebAppResourceNameForMetrics) {
    $settings += "AZURE_STATIC_WEB_APP_NAME=$StaticWebAppResourceNameForMetrics"
}

if ($PSCmdlet.ShouldProcess("$StaticWebAppName", "Set SWA app settings for Azure Monitor")) {
    $appsettingsArgs = @(
        "staticwebapp", "appsettings", "set",
        "-n", $StaticWebAppName,
        "-g", $StaticWebAppResourceGroup,
        "--subscription", $SubscriptionId,
        "--setting-names"
    ) + $settings
    Invoke-Az -Arguments $appsettingsArgs
    Write-Host "App settings updated."
}

# --- Managed identity + Reader ---
if (-not $SkipManagedIdentity) {
    $principalId = Get-SwaPrincipalId -Name $StaticWebAppName -ResourceGroup $StaticWebAppResourceGroup -Subscription $SubscriptionId

    if (-not $principalId) {
        if ($PSCmdlet.ShouldProcess("$StaticWebAppName", "Enable system-assigned identity + Reader on $monitorScope")) {
            Invoke-Az -Arguments @(
                "staticwebapp", "identity", "assign",
                "-n", $StaticWebAppName,
                "-g", $StaticWebAppResourceGroup,
                "--subscription", $SubscriptionId,
                "--role", "Reader",
                "--scope", $monitorScope
            )
            Write-Host "Managed identity enabled and Reader assigned (combined command)."
        }
    }
    else {
        Write-Host "System-assigned identity already present: $principalId"
        if ($PSCmdlet.ShouldProcess($monitorScope, "Grant Reader to $principalId")) {
            try {
                Invoke-Az -Arguments @(
                    "role", "assignment", "create",
                    "--assignee-object-id", $principalId,
                    "--role", "Reader",
                    "--scope", $monitorScope
                )
                Write-Host "Reader role assignment created (or az reported it already exists)."
            }
            catch {
                Write-Warning "Reader assignment may already exist: $_"
            }
        }
    }
}

# --- Optional: Cost Management Reader (subscription scope) ---
if ($AssignCostManagementReader) {
    $subScope = "/subscriptions/$SubscriptionId"
    $principalForCost = Get-SwaPrincipalId -Name $StaticWebAppName -ResourceGroup $StaticWebAppResourceGroup -Subscription $SubscriptionId
    if (-not $principalForCost) {
        Write-Warning "No principal id for Cost Management Reader; enable identity first."
    }
    elseif ($PSCmdlet.ShouldProcess($subScope, "Grant Cost Management Reader")) {
        try {
            Invoke-Az -Arguments @(
                "role", "assignment", "create",
                "--assignee-object-id", $principalForCost,
                "--role", "Cost Management Reader",
                "--scope", $subScope
            )
            Write-Host "Cost Management Reader assigned at subscription scope."
        }
        catch {
            Write-Warning "Cost Management Reader assignment may already exist or failed: $_"
        }
    }
}

Write-Host ""
Write-Host "Done. Redeploy or wait for the SWA API to pick up settings, then open Admin > Monitor > Refresh."
