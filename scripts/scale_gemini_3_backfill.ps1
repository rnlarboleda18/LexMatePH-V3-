$env:GOOGLE_API_KEY = "REDACTED_API_KEY_HIDDEN"
$env:DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

Write-Output "Launching 200 workers for Gemini 3 Backfill (Descending from 2025)..."

# Launch 200 workers (Restarting 1-50, Adding 51-200)
for ($i = 1; $i -le 200; $i++) {
    $logFile = "c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\logs\worker_gemini3_backfill_$i.log"
    # Note: Default sort is DESC (newest first), so no extra sort flag needed.
    Start-Job -ScriptBlock {
        param($id, $log)
        python c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\scripts\generate_sc_digests_gemini.py --model gemini-3-flash-preview --fix-gemini-3 --continuous --limit 10 2>&1 | Out-File $log
    } -ArgumentList $i, $logFile
}

Write-Output "Launched 200 workers."
