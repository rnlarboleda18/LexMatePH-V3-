<# 
  LexMatePH v3 — start local dev stack (cloud DB via api/local.settings.json).
  Order: optional Azurite → Azure Functions (:7071) → wait for /api/health → Vite (:5173).
#>

$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $Root

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   LexMatePH v3 — Startup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[CONFIG] Use cloud Postgres via api\local.settings.json with key DB_CONNECTION_STRING." -ForegroundColor DarkGray
Write-Host "         Do not set ENVIRONMENT=local unless you intend a local database." -ForegroundColor DarkGray
Write-Host ""

# ── Prerequisites ───────────────────────────────────────────────────────────
$apiDir       = Join-Path $Root "api"
$frontendDir  = Join-Path $Root "src\frontend"
$venvActivate = Join-Path $apiDir ".venv\Scripts\activate.bat"
$localSettings = Join-Path $apiDir "local.settings.json"

if (-not (Test-Path $localSettings)) {
    Write-Host "[FATAL] Missing $localSettings — copy from a template or create Values with DB_CONNECTION_STRING." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $venvActivate)) {
    Write-Host "[FATAL] Python venv not found: $venvActivate" -ForegroundColor Red
    Write-Host "        Run these commands:" -ForegroundColor Yellow
    Write-Host "          cd api" -ForegroundColor Yellow
    Write-Host "          python -m venv .venv" -ForegroundColor Yellow
    Write-Host "          .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[WARN]  node_modules missing — run: cd src\frontend && npm install" -ForegroundColor Yellow
}

$funcCmd = Get-Command func -ErrorAction SilentlyContinue
if (-not $funcCmd) {
    Write-Host "[FATAL] Azure Functions Core Tools not found. Install: npm i -g azure-functions-core-tools@4 --unsafe-perm" -ForegroundColor Red
    exit 1
}

# ── 1. Local Network IP ───────────────────────────────────────────────────────
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

Write-Host "[INFO] Frontend URLs:" -ForegroundColor Yellow
Write-Host "       http://$($localIp):5173" -ForegroundColor Green
Write-Host "       http://localhost:5173" -ForegroundColor Green
Write-Host "[INFO] API (proxied as /api): http://localhost:7071" -ForegroundColor Green
Write-Host ""

# ── 2. Public IP + Azure DB firewall pre-check ───────────────────────────────
Write-Host "[CHECK] Detecting public IP..." -ForegroundColor Yellow
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
        Write-Host "        [OK] Azure DB host is reachable (TCP)." -ForegroundColor Green
    }
    else {
        $tcpClient.Close()
        throw "TCP timeout"
    }
}
catch {
    Write-Host ""
    Write-Host "  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host "  !!  AZURE DB MAY BE FIREWALL-BLOCKED             !!" -ForegroundColor Red
    Write-Host "  !!  Your public IP [ $publicIp ]                 !!" -ForegroundColor Red
    Write-Host "  !!  Add it in Azure Portal > lexmateph-ea-db     !!" -ForegroundColor Red
    Write-Host "  !!  > Networking > Firewall rules                !!" -ForegroundColor Red
    Write-Host "  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Portal:" -ForegroundColor Yellow
    Write-Host "  https://portal.azure.com/#view/Microsoft_Azure_FluidRelay/PostGresFlexibleServerNetworkingBlade/subscriptionId/4a9c8f45-3889-4055-a2f0-097be69d078c/resourceGroupName/LexMatePH/serverName/lexmateph-ea-db" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [AUTO-CONTINUE] Proceeding with startup without confirmation." -ForegroundColor DarkYellow
}

# ── 3. Storage mode ──────────────────────────────────────────────────────────
Write-Host "`n[INFO] Storage: using Azure cloud storage (Azurite skipped)." -ForegroundColor Yellow

# ── 4. Azure Functions (API) — must be up before Vite uses /api proxy ───────
Write-Host "`n[INFO] Starting Azure Functions (new window)..." -ForegroundColor Yellow
$backendCmd = @"
@echo off
cd /d "$apiDir"
call .venv\Scripts\activate.bat
set PYTHONPATH=.
echo API directory: %CD%
echo Starting func host on http://localhost:7071 ...
func start
"@
$batPath = Join-Path $env:TEMP "lexmate_start_api.bat"
Set-Content -Path $batPath -Value $backendCmd -Encoding ASCII
Start-Process cmd -ArgumentList "/k", "`"$batPath`""

# ── 5. Wait until API responds ──────────────────────────────────────────────
Write-Host "[WAIT] Polling http://localhost:7071/api/health ..." -ForegroundColor Yellow
$healthUrl = "http://localhost:7071/api/health"
$ready = $false
$maxWaitSec = 120
$elapsedSec = 0
$sleepSec = 1
$maxSleepSec = 6

while ($elapsedSec -lt $maxWaitSec) {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Host "       [OK] API health endpoint is ready." -ForegroundColor Green
            $ready = $true
            break
        }
    }
    catch {
        # host may still be starting
    }

    # Early success: if the host is already listening on 7071, continue startup.
    try {
        $probe = New-Object System.Net.Sockets.TcpClient
        $ar = $probe.BeginConnect("127.0.0.1", 7071, $null, $null)
        if ($ar.AsyncWaitHandle.WaitOne(400, $false) -and $probe.Connected) {
            $probe.EndConnect($ar)
            $probe.Close()
            Write-Host "       [OK] API host is listening on :7071 (health endpoint not ready yet)." -ForegroundColor Green
            $ready = $true
            break
        }
        $probe.Close()
    }
    catch {
        # ignore probe failures while booting
    }

    Write-Host "       ... still waiting ($elapsedSec s)" -ForegroundColor DarkGray
    Start-Sleep -Seconds $sleepSec
    $elapsedSec += $sleepSec
    $sleepSec = [Math]::Min($maxSleepSec, [Math]::Ceiling($sleepSec * 1.5))
}

if (-not $ready) {
    Write-Host "       [WARN] API health/listen check did not succeed in ${maxWaitSec}s. Open the API window for errors; starting Vite anyway." -ForegroundColor DarkYellow
}

# ── 6. Vite frontend ────────────────────────────────────────────────────────
Write-Host "`n[INFO] Starting Vite (new window)..." -ForegroundColor Yellow
$viteCmd = @"
@echo off
cd /d "$frontendDir"
if not exist node_modules (
  echo Running npm install ...
  call npm install
)
echo Frontend: %CD%
npm run dev -- --host 0.0.0.0
"@
$viteBat = Join-Path $env:TEMP "lexmate_start_vite.bat"
Set-Content -Path $viteBat -Value $viteCmd -Encoding ASCII
Start-Process cmd -ArgumentList "/k", "`"$viteBat`""

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Done. Two CMD windows: API + Vite." -ForegroundColor Green
Write-Host "  Close those windows or run restart_all.ps1 to stop." -ForegroundColor DarkGray
Write-Host "==========================================" -ForegroundColor Cyan
