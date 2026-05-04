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

---

## Case digest / E-Library pipeline (admin + local `func start`)

These scripts run against the **cloud** database via `DB_CONNECTION_STRING` (merged from `api/local.settings.json` / repo root `local.settings.json` by `scripts/load_local_settings_env.py`). The Admin Digest Pipeline tab starts **`elib_digest_pipeline.py`** from the Functions process using **`sys.executable`**.

Run from repo root (`python scripts/…`). Other env keys: see `api/local.settings.sample.json` (Gemini/Vertex, `GOOGLE_API_KEY`, optional `XAI_API_KEY`, `DIGEST_SAFETY_FALLBACK_MODEL`, etc.).

| Script | Purpose |
|--------|---------|
| `elib_digest_pipeline.py` | Main flow: probe eLib IDs, HTML→Markdown, insert `sc_decided_cases`, digests (Gemini + optional Grok safety fallback), codal linking. Flags include `--progress-file` for JSON progress snapshots. |
| `finish_elib_pipeline_digests.py` | Resume/finish digest (and related) work for rows that did not complete in a prior run. |
| `digest_pipeline_progress.py` | Library: thread-safe **atomic** `pipeline_progress.json` writer (retries on Windows replace **access denied**). |
| `scan_elib_new_cases.py` | Read-only scan: find new showdocs URLs not yet in `sc_decided_cases`; writes `admin-tools/case-digest-pipeline/scan_results.json` (also used by Admin **Scan eLib**). |
| `scan_elib_gaps.py` | Gap scan for missing G.R. ranges (see script docstring). |
| `list_cases_added_today.py` | List rows inserted “today” by **`created_at`**: `--tz utc` (default) or `--tz manila` (naive UTC column interpreted consistently). |

**Runtime artifacts (gitignored or local-only):** `admin-tools/case-digest-pipeline/pipeline_progress.json`, `pipeline_subprocess.log`, scan/gap JSON—do not treat them as source of truth in git.

**Operational note:** If `/api/ops/*` returns **404** but `/api/ping` works, restart **`func start`** from `api/` so blueprints load — see **`docs/RUNBOOK.md` § Admin Digest Pipeline** and **`docs/adr/005-admin-case-digest-pipeline.md`**.

**Duplicate scan entrypoints:** copies under `api/scripts/` exist for Azure bundle paths; prefer `scripts/` at repo root for workstation runs unless you are debugging the deployed layout.
