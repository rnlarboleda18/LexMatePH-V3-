# Scale Up Fleets Script
# Target: 100 Ascending + 100 Descending Workers (Total 200)

$env:GOOGLE_API_KEY = "REDACTED_API_KEY_HIDDEN"
$env:DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

Write-Host "--- SCALING UP FLEETS TO 200 WORKERS ---" -ForegroundColor Cyan

# 1. KILL ALL EXISTING WORKERS
Write-Host "Killing all existing digest workers..." -ForegroundColor Red
$processes = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like "*generate_sc_digests_gemini.py*" }

if ($processes) {
    foreach ($proc in $processes) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Killed $($processes.Count) existing workers." -ForegroundColor Green
}
else {
    Write-Host "No active workers found to kill." -ForegroundColor Yellow
}

# 2. ASCENDING FLEET (100 Workers)
Write-Host "Launching 100 Ascending Workers (1901-1989)..." -ForegroundColor Green
for ($i = 1; $i -le 100; $i++) {
    Start-Process -FilePath "python" -ArgumentList "scripts/generate_sc_digests_gemini.py --start-year 1901 --end-year 1989 --model gemini-2.5-flash-lite --ascending --continuous --limit 500" -WindowStyle Minimized
    Start-Sleep -Milliseconds 100
    if ($i % 10 -eq 0) { Write-Host "Launched $i/100 Ascending..." -NoNewline; Write-Host "." }
}

# 3. DESCENDING FLEET (100 Workers)
Write-Host "`nLaunching 100 Descending Workers (1990-2025)..." -ForegroundColor Yellow
for ($j = 1; $j -le 100; $j++) {
    Start-Process -FilePath "python" -ArgumentList "scripts/generate_sc_digests_gemini.py --start-year 1990 --end-year 2025 --model gemini-2.5-flash-lite --continuous --limit 500" -WindowStyle Minimized
    Start-Sleep -Milliseconds 100
    if ($j % 10 -eq 0) { Write-Host "Launched $j/100 Descending..." -NoNewline; Write-Host "." }
}

Write-Host "`nAll 200 Workers Launched Successfully!" -ForegroundColor White
