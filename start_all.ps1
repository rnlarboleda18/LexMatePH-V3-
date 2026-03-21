Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Bar Project V2 - Startup Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get Local IP Address
try {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
            $_.InterfaceAlias -notlike "*Loopback*" -and 
            $_.InterfaceAlias -notlike "*vEthernet*" -and 
            $_.IPAddress -notlike "169.254*" 
        } | Select-Object -First 1).IPAddress
}
catch {
    $ip = "Unknown"
}

Write-Host "`n[INFO] Local Network Access URL:" -ForegroundColor Yellow
Write-Host "       http://$($ip):5173" -ForegroundColor Green
Write-Host "       http://localhost:5173" -ForegroundColor Green

Write-Host "[INFO] Starting LexPlay Storage (Azurite via Docker)..."
Start-Process cmd -ArgumentList "/c", "docker run -d -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0"

Write-Host "[INFO] Starting Backend (Azure Functions)..."
# Force use of virtual environment python and set PYTHONPATH to allow importing from utils package
Start-Process cmd -ArgumentList "/k", "cd api && .venv\Scripts\activate && set PYTHONPATH=. && echo Starting Backend... && func start"

Write-Host "[INFO] Starting Frontend (Vite Dev Server)..."
Start-Process cmd -ArgumentList "/k", "cd src/frontend && npm run dev -- --host 0.0.0.0"

Write-Host "       Press Ctrl+C to stop the web server.`n"
