# Bar Project V2 - Restart All Applications
Write-Host "=========================================="
Write-Host "   Bar Project V2 - Restart Script"
Write-Host "=========================================="
Write-Host ""

# Kill all running processes
Write-Host "[INFO] Stopping all node and func processes..."
Get-Process | Where-Object {$_.ProcessName -like "*node*" -or $_.ProcessName -like "*func*" -or $_.ProcessName -like "*swa*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Wait for processes to fully terminate
Start-Sleep -Seconds 2

# Relaunch using start_all.ps1
Write-Host "[INFO] Relaunching applications..."
& ".\start_all.ps1"
