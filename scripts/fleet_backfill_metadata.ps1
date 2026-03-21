$numWorkers = 100
$apiKey = "REDACTED_API_KEY_HIDDEN" # Legacy Key (High Quota)
$model = "gemini-2.5-flash-lite"
$pythonScript = "scripts/generate_sc_digests_gemini.py"
# Metadata Backfill - explicitly targeting missing core fields
$appArgs = "--metadata-backfill --continuous --limit 500 --model $model"

Write-Host "Launching METADATA BACKFILL FLEET (100 Workers)..." -ForegroundColor Magenta

for ($i = 1; $i -le $numWorkers; $i++) {
    Write-Host "Starting Metadata Worker #$i..." -ForegroundColor Green
    # No Year Range - we want to catch the "invisible" NULL date cases
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:GOOGLE_API_KEY = '$apiKey'; python $pythonScript $appArgs; Read-Host 'Metadata Worker Finished. Press Enter...'"
    Start-Sleep -Milliseconds 200
}
