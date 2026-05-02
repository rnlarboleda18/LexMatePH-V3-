# Azure Communication — Email: customer-managed custom domain, verification, sender, app settings.
#
# Prereq: Azure CLI 2.67+ (installs the `communication` extension on first use), `az login`, and
#   permission to manage the Email Communication resource and (optional) app settings on your host.
# DNS: You must add TXT/SPF/DKIM (and any other) records at your DNS host using values from
#   ShowDomain (see Microsoft Learn: "Add a custom verified domain" for ACS Email).
#
# Typical sequence (replace names if yours differ; defaults match this repo’s notes):
#   1) .\acs_email_custom_domain.ps1 -Action ListEmailServices
#   2) .\acs_email_custom_domain.ps1 -Action CreateDomain
#   3) .\acs_email_custom_domain.ps1 -Action ShowDomain
#   4) Add each DNS record from the JSON to your zone; wait for propagation.
#   5) .\acs_email_custom_domain.ps1 -Action InitiateVerifications
#   6) Re-run InitiateVerifications and ShowDomain until verification status is satisfied (portal/CLI may show per-record state).
#   7) .\acs_email_custom_domain.ps1 -Action CreateSender
#   8) Set `ACS_SENDER_EMAIL` to "<SenderLocalPart>@<DomainName>" in local.settings.json and in Azure.
#   9) If the API is hosted on Azure Static Web Apps (this repo: api_location "api"), set app settings on the
#      SWA resource (not a standalone Function App):
#        .\acs_email_custom_domain.ps1 -Action SetStaticWebAppSettings
#      Or use a standalone Function App if you have one:
#        .\acs_email_custom_domain.ps1 -Action SetFunctionAppSettings -FunctionAppName "<your-funcapp>"
#
# Reference: https://learn.microsoft.com/en-us/cli/azure/communication/email/domain

param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('ListEmailServices', 'CreateDomain', 'ShowDomain', 'InitiateVerifications', 'CreateSender', 'SetStaticWebAppSettings', 'SetFunctionAppSettings')]
  [string] $Action,
  [string] $ResourceGroup = 'LexMatePH',
  [string] $EmailServiceName = 'lexmateph-email',
  [string] $DomainName = 'lexmateph.com',
  [string] $SenderLocalPart = 'DoNotReply',
  [string] $StaticWebAppName = 'swa-lexmateph-us',
  [string] $FunctionAppName = '',
  [string] $SenderDisplayName = 'LexMatePH'
)

$ErrorActionPreference = 'Stop'

function Assert-AzAvailable {
  if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Azure CLI (az) not found. Install from https://learn.microsoft.com/en-us/cli/azure/install-azure-cli'
  }
}

function Get-EmailServiceAzArgs {
  return @(
    '--resource-group', $ResourceGroup,
    '--email-service-name', $EmailServiceName
  )
}

Assert-AzAvailable

switch ($Action) {
  'ListEmailServices' {
    Write-Host "Email Communication resources in $ResourceGroup :"
    az resource list -g $ResourceGroup --query "[?type=='Microsoft.Communication/EmailServices']" -o table
  }
  'CreateDomain' {
    $azArgs = @(
      'communication', 'email', 'domain', 'create',
      '--name', $DomainName,
      '--domain-name', $DomainName
    ) + (Get-EmailServiceAzArgs) + @(
      '--location', 'global',
      '--domain-management', 'CustomerManaged'
    )
    Write-Host "Creating customer-managed domain $DomainName ..."
    az @azArgs
  }
  'ShowDomain' {
    $azArgs = @(
      'communication', 'email', 'domain', 'show',
      '--name', $DomainName,
      '--domain-name', $DomainName
    ) + (Get-EmailServiceAzArgs)
    Write-Host "Domain resource (use properties for required DNS / verification state):"
    az @azArgs -o jsonc
  }
  'InitiateVerifications' {
    # DMARC is not a valid --verification-type for this API (returns InitiateVerificationFailed).
    $types = @('Domain', 'SPF', 'DKIM', 'DKIM2')
    foreach ($vt in $types) {
      Write-Host "Initiating verification: $vt ..."
      $azArgs = @(
        'communication', 'email', 'domain', 'initiate-verification',
        '--domain-name', $DomainName
      ) + (Get-EmailServiceAzArgs) + @(
        '--verification-type', $vt
      )
      az @azArgs
      if ($LASTEXITCODE -ne 0) { Write-Warning "Verification $vt did not complete successfully (code $LASTEXITCODE). DNS may be missing or not propagated yet." }
    }
  }
  'CreateSender' {
    if ([string]::IsNullOrWhiteSpace($SenderLocalPart)) { throw 'SenderLocalPart is required (e.g. DoNotReply).' }
    $azArgs = @(
      'communication', 'email', 'domain', 'sender-username', 'create'
    ) + (Get-EmailServiceAzArgs) + @(
      '--domain-name', $DomainName,
      '--sender-username', $SenderLocalPart,
      '--username', $SenderLocalPart
    )
    Write-Host "Creating sender $SenderLocalPart@$DomainName ..."
    az @azArgs
    if (-not [string]::IsNullOrWhiteSpace($SenderDisplayName)) {
      $upArgs = @(
        'communication', 'email', 'domain', 'sender-username', 'update'
      ) + (Get-EmailServiceAzArgs) + @(
        '--domain-name', $DomainName,
        '--sender-username', $SenderLocalPart,
        '--display-name', $SenderDisplayName
      )
      az @upArgs
    }
  }
  'SetStaticWebAppSettings' {
    if ([string]::IsNullOrWhiteSpace($StaticWebAppName)) { throw 'Pass -StaticWebAppName (default: swa-lexmateph-us).' }
    $from = "$SenderLocalPart@$DomainName"
    Write-Host "Setting ACS_SENDER_EMAIL=$from on Static Web App $StaticWebAppName (API uses these app settings) ..."
    az staticwebapp appsettings set -n $StaticWebAppName -g $ResourceGroup --setting-names "ACS_SENDER_EMAIL=$from" -o json
  }
  'SetFunctionAppSettings' {
    if ([string]::IsNullOrWhiteSpace($FunctionAppName)) { throw 'Pass -FunctionAppName for the Azure Function App (API) name.' }
    $from = "$SenderLocalPart@$DomainName"
    Write-Host "Setting ACS_SENDER_EMAIL=$from on Function App $FunctionAppName ..."
    az functionapp config appsettings set -g $ResourceGroup -n $FunctionAppName --settings "ACS_SENDER_EMAIL=$from" -o table
  }
}
