$numWorkers = 150
$apiKey = "REDACTED_API_KEY_HIDDEN"
$model = "gemini-2.5-flash-lite"
$pythonScript = "scripts/generate_sc_digests_gemini.py"
# Sweeper range: 1901-1989 (Improved Logic enabled in python script default)
$appArgs = "--start-year 1901 --end-year 1989 --continuous --limit 500 --model $model"

Write-Host "Launching SWEEPER FLEET (1901-1989) with $numWorkers Workers (Search & Destroy)..." -ForegroundColor Magenta

for ($i = 1; $i -le $numWorkers; $i++) {
    Write-Host "Starting Sweeper Worker #$i..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:GOOGLE_API_KEY = '$apiKey'; python $pythonScript $appArgs; Read-Host 'Sweeper Finished. Press Enter...'"
    Start-Sleep -Milliseconds 200
}
