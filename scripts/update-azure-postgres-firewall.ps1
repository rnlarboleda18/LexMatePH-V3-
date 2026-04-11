#Requires -Version 5.1
<#
.SYNOPSIS
  Sets an Azure Database for PostgreSQL Flexible Server firewall rule to this PC's current public IPv4.

.DESCRIPTION
  Fetches public IP (api.ipify.org), then creates or updates a named rule via Azure CLI.

  Prereqs: Azure CLI installed, authenticated (`az login`).
  Targets Flexible Server only (current `az postgres` CLI).

.PARAMETER ResourceGroup
  Azure resource group containing the server.

.PARAMETER ServerName
  PostgreSQL flexible server name only (not the full hostname).

.PARAMETER RuleName
  Firewall rule name to create or reuse (default: dev-home-pc).

.EXAMPLE
  .\update-azure-postgres-firewall.ps1 -ResourceGroup my-rg -ServerName mypgserver

.EXAMPLE
  $env:AZURE_POSTGRES_RG = 'my-rg'; $env:AZURE_POSTGRES_SERVER = 'mypgserver'; .\update-azure-postgres-firewall.ps1
#>
param(
    [Parameter(Mandatory = $false)]
    [string] $ResourceGroup = $env:AZURE_POSTGRES_RG,

    [Parameter(Mandatory = $false)]
    [string] $ServerName = $env:AZURE_POSTGRES_SERVER,

    [string] $RuleName = 'dev-home-pc'
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Azure CLI not found. Install from https://aka.ms/installazurecliwindows then run az login.'
}

if ([string]::IsNullOrWhiteSpace($ResourceGroup) -or [string]::IsNullOrWhiteSpace($ServerName)) {
    throw 'Set -ResourceGroup and -ServerName, or environment variables AZURE_POSTGRES_RG and AZURE_POSTGRES_SERVER.'
}

$ip = (Invoke-RestMethod -Uri 'https://api.ipify.org' -TimeoutSec 20).ToString().Trim()
if ($ip -notmatch '^\d{1,3}(\.\d{1,3}){3}$') {
    throw "Unexpected IP response: $ip"
}

Write-Host "Public IPv4: $ip"
Write-Host "Rule: $RuleName | Server: $ServerName | RG: $ResourceGroup"

function Invoke-Az {
    param([string[]] $Args)
    & az @Args
    if ($LASTEXITCODE -ne 0) {
        throw "az failed: az $($Args -join ' ')"
    }
}

# Use list, not show: `show` for a missing rule can error as if the *server* were missing (CLI quirk).
$rulesJson = az postgres flexible-server firewall-rule list `
    --resource-group $ResourceGroup `
    --name $ServerName -o json
if ($LASTEXITCODE -ne 0) {
    throw "az postgres flexible-server firewall-rule list failed."
}
$rules = $rulesJson | ConvertFrom-Json
$existing = $rules | Where-Object { $_.name -eq $RuleName }

if ($existing) {
    Write-Host 'Updating existing firewall rule...'
    Invoke-Az @(
        'postgres', 'flexible-server', 'firewall-rule', 'update',
        '--resource-group', $ResourceGroup,
        '--name', $ServerName,
        '--rule-name', $RuleName,
        '--start-ip-address', $ip,
        '--end-ip-address', $ip
    )
}
else {
    Write-Host 'Creating firewall rule...'
    Invoke-Az @(
        'postgres', 'flexible-server', 'firewall-rule', 'create',
        '--resource-group', $ResourceGroup,
        '--name', $ServerName,
        '--rule-name', $RuleName,
        '--start-ip-address', $ip,
        '--end-ip-address', $ip
    )
}

Write-Host 'Done.'
