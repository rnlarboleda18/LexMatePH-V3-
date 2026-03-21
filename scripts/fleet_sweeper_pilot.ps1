$numWorkers = 10
$apiKey = "REDACTED_API_KEY_HIDDEN"
$model = "gemini-2.5-flash-lite"
$pythonScript = "scripts/generate_sc_digests_gemini.py"
# Sweeper range: 1901-1989
$appArgs = "--start-year 1901 --end-year 1989 --continuous --limit 500 --model $model"

Write-Host "Launching SWEEPER PILOT (1901-1989) with $numWorkers Workers..." -ForegroundColor Magenta

for ($i = 1; $i -le $numWorkers; $i++) {
    Write-Host "Starting Pilot Worker #$i..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:GOOGLE_API_KEY = '$apiKey'; python $pythonScript $appArgs; Read-Host 'Pilot Finished. Press Enter...'"
    Start-Sleep -Milliseconds 200
}
