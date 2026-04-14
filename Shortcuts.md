# Shortcuts

PowerShell launchers for common tasks. From a terminal, `cd` to the repo root, then run the script path (or use **Run with PowerShell** on the file in Explorer; you may need `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once).

| What | Run |
|------|-----|
| **E-Library case digest pipeline** (fetch, MD named by case + date, DB, Gemini digest) | [`admin-tools/case-digest-pipeline/Run-ElibCaseDigestPipeline.ps1`](admin-tools/case-digest-pipeline/Run-ElibCaseDigestPipeline.ps1) |
| Same (legacy filename) | [`admin-tools/case-digest-pipeline/run-elib-pipeline.ps1`](admin-tools/case-digest-pipeline/run-elib-pipeline.ps1) |
| ROC linking batch (if you use it) | [`scripts/run_roc_linking_batch.ps1`](scripts/run_roc_linking_batch.ps1) |

## E-Library pipeline examples (PowerShell)

```powershell
cd "C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3"

# Scan for new showdocs IDs after DB max, full pipeline
.\admin-tools\case-digest-pipeline\Run-ElibCaseDigestPipeline.ps1

# Specific E-Library numeric IDs
.\admin-tools\case-digest-pipeline\Run-ElibCaseDigestPipeline.ps1 --ids 70193,70194
```

Double-click alternative: repo root **`run-elib-pipeline.cmd`** calls the same PowerShell script.

Secrets: use **`local.settings.json`** (repo root or `api/`) with `DB_CONNECTION_STRING` and `GOOGLE_API_KEY` (never commit real values).
