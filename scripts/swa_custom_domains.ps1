# Azure Static Web App — list or add custom hostnames (lexmateph.com / www)
# Prereq: az login, subscription with SWA "swa-lexmateph-us" in resource group "LexMatePH"
#
# List current hostnames and status:
#   .\scripts\swa_custom_domains.ps1
#
# Add www (CNAME to Azure; default validation):
#   .\scripts\swa_custom_domains.ps1 -AddWww
#
# Add apex domain (uses TXT token validation in Azure):
#   .\scripts\swa_custom_domains.ps1 -AddApex
#
# After any add, finish DNS at your registrar as shown by Azure Portal or:
#   az staticwebapp hostname show -n swa-lexmateph-us -g LexMatePH --name www.lexmateph.com

param(
  [switch] $ListOnly,
  [switch] $AddWww,
  [switch] $AddApex
)

$Name = "swa-lexmateph-us"
$Rg   = "LexMatePH"

if ($AddWww) {
  az staticwebapp hostname set -n $Name -g $Rg --hostname "www.lexmateph.com" --validation-method cname-delegation
} elseif ($AddApex) {
  az staticwebapp hostname set -n $Name -g $Rg --hostname "lexmateph.com" --validation-method dns-txt-token
} else {
  az staticwebapp hostname list -n $Name -g $Rg -o table
}
