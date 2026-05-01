# Scripts

## `configure_swa_azure_monitor.ps1`

Configures **Azure Static Web App** application settings and **managed identity + RBAC** so the production Admin **Monitor** tab (`/api/ops/azure-metrics`) can read Azure Monitor metrics.

**Prerequisites:** Azure CLI, `az login`, rights to edit the SWA and create role assignments.

**Example:**

```powershell
.\scripts\configure_swa_azure_monitor.ps1 `
  -StaticWebAppName "<your-swa-name>" `
  -StaticWebAppResourceGroup "<rg-where-swa-lives>" `
  -MonitorResourceGroup "<rg-with-postgres>" `
  -PostgresServerName "<flex-server-name>" `
  -AssignCostManagementReader
```

Use `-WhatIf` to preview. If identity is already enabled, the script adds a **Reader** role on the monitor resource group when missing. Optional `-SkipManagedIdentity` only sets `AZURE_*` app settings.

**Same steps by hand (Azure CLI):**

```bash
SUB="<subscription-guid>"
SWA_RG="<resource-group-of-static-web-app>"
SWA_NAME="<static-web-app-name>"
MON_RG="<resource-group-containing-postgres-and-monitored-resources>"
SCOPE="/subscriptions/$SUB/resourceGroups/$MON_RG"

az staticwebapp appsettings set -n "$SWA_NAME" -g "$SWA_RG" --subscription "$SUB" \
  --setting-names "AZURE_SUBSCRIPTION_ID=$SUB" "AZURE_RESOURCE_GROUP=$MON_RG"

az staticwebapp identity assign -n "$SWA_NAME" -g "$SWA_RG" --subscription "$SUB" \
  --role Reader --scope "$SCOPE"

# Optional — cost panel in Monitor (subscription scope):
PRINCIPAL="$(az staticwebapp identity show -n "$SWA_NAME" -g "$SWA_RG" --subscription "$SUB" --query principalId -o tsv)"
az role assignment create --assignee-object-id "$PRINCIPAL" --role "Cost Management Reader" \
  --scope "/subscriptions/$SUB"
```

## `rotate_swa_monitor_sp_secret.py`

Rotates the Entra **client secret** for the Monitor service principal and writes **`AZURE_CLIENT_SECRET`** on the Static Web App (does not print the secret).

```bash
python scripts/rotate_swa_monitor_sp_secret.py \
  --app-id "<app-registration-id>" \
  --subscription "<subscription-guid>" \
  --swa-name "<static-web-app-name>" \
  --resource-group "<swa-resource-group>"
```

Plain **`az`** equivalent: `az ad app credential reset --id <appId> -o json` (read `password`), then `az staticwebapp appsettings set ... --setting-names "AZURE_CLIENT_SECRET=..."`, then delete old credentials with `az ad app credential list` / `credential delete`.
