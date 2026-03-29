Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   LexMatePH-V3 - Startup Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# ── 1. Get Local Network IP ──────────────────────────────────────────────────
try {
    $localIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
            $_.InterfaceAlias -notlike "*Loopback*" -and
            $_.InterfaceAlias -notlike "*vEthernet*" -and
            $_.IPAddress -notlike "169.254*"
        } | Select-Object -First 1).IPAddress
}
catch {
    $localIp = "Unknown"
}

Write-Host "`n[INFO] Local Network Access URL:" -ForegroundColor Yellow
Write-Host "       http://$($localIp):5173" -ForegroundColor Green
Write-Host "       http://localhost:5173" -ForegroundColor Green

# ── 2. Public IP + Azure DB Firewall Pre-Check ───────────────────────────────
Write-Host "`n[CHECK] Detecting public IP..." -ForegroundColor Yellow
try {
    $publicIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing -TimeoutSec 5).Content.Trim()
    Write-Host "        Public IP: $publicIp" -ForegroundColor Cyan
}
catch {
    $publicIp = "Unknown"
    Write-Host "        Could not detect public IP." -ForegroundColor DarkYellow
}

Write-Host "[CHECK] Testing Azure DB connectivity (port 5432)..." -ForegroundColor Yellow
$dbHost = "lexmateph-ea-db.postgres.database.azure.com"
$dbPort = 5432
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $connectResult = $tcpClient.BeginConnect($dbHost, $dbPort, $null, $null)
    $waitResult = $connectResult.AsyncWaitHandle.WaitOne(5000, $false)
    if ($waitResult -and $tcpClient.Connected) {
        $tcpClient.EndConnect($connectResult)
        $tcpClient.Close()
        Write-Host "        [OK] Azure DB is reachable!" -ForegroundColor Green
    }
    else {
        $tcpClient.Close()
        throw "TCP timeout"
    }
}
catch {
    Write-Host "" 
    Write-Host "  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host "  !!  AZURE DB FIREWALL BLOCKED                 !!" -ForegroundColor Red
    Write-Host "  !!                                            !!" -ForegroundColor Red
    Write-Host "  !!  Your public IP [ $publicIp ] is          !!" -ForegroundColor Red
    Write-Host "  !!  NOT whitelisted in Azure DB Firewall.     !!" -ForegroundColor Red
    Write-Host "  !!                                            !!" -ForegroundColor Red
    Write-Host "  !!  Fix: Go to Azure Portal > lexmateph-ea-db !!" -ForegroundColor Red
    Write-Host "  !!  > Networking > Firewall rules             !!" -ForegroundColor Red
    Write-Host "  !!  > Add current client IP > Save            !!" -ForegroundColor Red
    Write-Host "  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Direct link:" -ForegroundColor Yellow
    Write-Host "  https://portal.azure.com/#view/Microsoft_Azure_FluidRelay/PostGresFlexibleServerNetworkingBlade/subscriptionId/4a9c8f45-3889-4055-a2f0-097be69d078c/resourceGroupName/LexMatePH/serverName/lexmateph-ea-db" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "  Start anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host "Aborted. Fix the firewall rule and re-run start_all.ps1." -ForegroundColor Red
        exit 1
    }
}

# ── 3. Start Services ─────────────────────────────────────────────────────────
Write-Host "`n[INFO] Starting LexPlay Storage (Azurite via Docker)..."
Start-Process cmd -ArgumentList "/c", "docker run -d -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0"

Write-Host "[INFO] Starting Backend (Azure Functions)..."
Start-Process cmd -ArgumentList "/k", "cd api && .venv\Scripts\activate && set PYTHONPATH=. && echo Starting Backend... && func start"

Write-Host "[INFO] Starting Frontend (Vite Dev Server)..."
Start-Process cmd -ArgumentList "/k", "cd src/frontend && npm run dev -- --host 0.0.0.0"

Write-Host "       Press Ctrl+C to stop the web server.`n"
