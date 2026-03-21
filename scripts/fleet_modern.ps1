$numWorkers = 30
$apiKey = "REDACTED_API_KEY_HIDDEN"
$model = "gemini-3-flash-preview"
$pythonScript = "scripts/generate_sc_digests_gemini.py"
$appArgs = "--start-year 1990 --end-year 2025 --continuous --limit 500 --model $model"

Write-Host "Launching Modern Fleet (1990-2025) with $numWorkers Workers (Gemini 3 Preview) - New Key..." -ForegroundColor Cyan

for ($i = 1; $i -le $numWorkers; $i++) {
    Write-Host "Starting Modern Worker #$i..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:GOOGLE_API_KEY = '$apiKey'; python $pythonScript $appArgs; Read-Host 'Worker Finished. Press Enter...'"
    Start-Sleep -Milliseconds 200
}
