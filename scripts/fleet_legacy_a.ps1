$numWorkers = 50
$apiKey = "REDACTED_API_KEY_HIDDEN"
$model = "gemini-2.5-flash-lite"
$pythonScript = "scripts/generate_sc_digests_gemini.py"
$appArgs = "--start-year 1901 --end-year 1945 --ascending --continuous --limit 500 --model $model"

Write-Host "Launching Legacy Fleet A (1901-1945) with $numWorkers Workers (Lite) - New Key..." -ForegroundColor Cyan

for ($i = 1; $i -le $numWorkers; $i++) {
    Write-Host "Starting Legacy A Worker #$i..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:GOOGLE_API_KEY = '$apiKey'; python $pythonScript $appArgs; Read-Host 'Worker Finished. Press Enter...'"
    Start-Sleep -Milliseconds 200
}
