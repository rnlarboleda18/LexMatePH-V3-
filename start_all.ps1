<#
  LexMatePH v3 - start local dev stack (cloud DB via api/local.settings.json).
  Order: Azure Functions (:7071) -> wait -> Vite (:5173) -> wait -> SWA (:4280)
         Admin backend (:8000) + Admin frontend (:3000) started alongside.
#>

$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $Root

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   LexMatePH v3 - Startup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[CONFIG] Cloud Postgres via api\local.settings.json (DB_CONNECTION_STRING)." -ForegroundColor DarkGray
Write-Host ""

# Clear stale env vars that would shadow local.settings.json
$env:DB_CONNECTION_STRING = $null
$env:ENVIRONMENT = $null

# -- Paths --------------------------------------------------------------------
$apiDir           = Join-Path $Root "api"
$frontendDir      = Join-Path $Root "src\frontend"
$adminBackendDir  = Join-Path $Root "admin_app\backend"
$adminFrontendDir = Join-Path $Root "admin_app\frontend"
$venvActivate     = Join-Path $apiDir ".venv\Scripts\activate.bat"
$adminVenvPython  = Join-Path $adminBackendDir ".venv\Scripts\python.exe"
$localSettings    = Join-Path $apiDir "local.settings.json"

# -- Prerequisites ------------------------------------------------------------
if (-not (Test-Path $localSettings)) {
    Write-Host "[FATAL] Missing $localSettings" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $venvActivate)) {
    Write-Host "[FATAL] Python venv not found: $venvActivate" -ForegroundColor Red
    Write-Host "        cd api && python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[WARN]  node_modules missing - run: cd src\frontend && npm install" -ForegroundColor Yellow
}
if (-not (Test-Path $adminVenvPython)) {
    Write-Host "[WARN]  Admin backend venv not found. To set it up:" -ForegroundColor Yellow
    Write-Host "          cd admin_app\backend" -ForegroundColor Yellow
    Write-Host "          python -m venv .venv" -ForegroundColor Yellow
    Write-Host "          .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host "        Admin backend (port 8000) will be skipped." -ForegroundColor DarkYellow
}
if (-not (Test-Path (Join-Path $adminFrontendDir "node_modules"))) {
    Write-Host "[WARN]  admin_app\frontend\node_modules missing - run: cd admin_app\frontend && npm install" -ForegroundColor Yellow
}

$funcCmd = Get-Command func -ErrorAction SilentlyContinue
if (-not $funcCmd) {
    Write-Host "[FATAL] Azure Functions Core Tools not found. Install: npm i -g azure-functions-core-tools@4 --unsafe-perm" -ForegroundColor Red
    exit 1
}

# -- Local IP -----------------------------------------------------------------
try {
    $localIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.InterfaceAlias -notlike "*Loopback*" -and
        $_.InterfaceAlias -notlike "*vEthernet*" -and
        $_.IPAddress -notlike "169.254*"
    } | Select-Object -First 1).IPAddress
} catch { $localIp = "Unknown" }

Write-Host "[INFO] Access URLs once running:" -ForegroundColor Yellow
Write-Host "       Main app  (SWA):         http://localhost:4280" -ForegroundColor Green
Write-Host "       Main app  (Vite direct): http://localhost:5173" -ForegroundColor DarkGray
Write-Host "       Main API  (Functions):   http://localhost:7071" -ForegroundColor DarkGray
Write-Host "       Admin app (Next.js):     http://localhost:3000" -ForegroundColor Green
Write-Host "       Admin API (FastAPI):     http://localhost:8000" -ForegroundColor Green
Write-Host "       LAN:                     http://$($localIp):4280" -ForegroundColor Green
Write-Host ""

# -- Azure DB firewall auto-update --------------------------------------------
$azRg         = "LexMatePH"
$azServer     = "lexmateph-ea-db"
$azRuleName   = "dev-dynamic-ip"

Write-Host "[CHECK] Detecting public IP..." -ForegroundColor Yellow
try {
    $publicIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing -TimeoutSec 5).Content.Trim()
    Write-Host "        Public IP: $publicIp" -ForegroundColor Cyan
} catch {
    $publicIp = $null
    Write-Host "        Could not detect public IP - skipping firewall update." -ForegroundColor DarkYellow
}

if ($publicIp) {
    $azCmd = Get-Command az -ErrorAction SilentlyContinue
    if (-not $azCmd) {
        Write-Host "[WARN]  Azure CLI not found - cannot auto-update firewall. Install from https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    } else {
        # Check if the rule already has this IP (skip the az call if unchanged)
        $existingIp = az postgres flexible-server firewall-rule show `
            --resource-group $azRg --name $azServer --rule-name $azRuleName `
            --query "startIpAddress" -o tsv 2>$null
        if ($existingIp -eq $publicIp) {
            Write-Host "        [OK] Firewall rule '$azRuleName' already set to $publicIp." -ForegroundColor Green
        } else {
            Write-Host "        Updating firewall rule '$azRuleName' to $publicIp ..." -ForegroundColor Yellow
            $out = az postgres flexible-server firewall-rule create `
                --resource-group $azRg --name $azServer --rule-name $azRuleName `
                --start-ip-address $publicIp --end-ip-address $publicIp 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "        [OK] Firewall updated." -ForegroundColor Green
            } else {
                Write-Host "        [WARN] Firewall update failed: $out" -ForegroundColor DarkYellow
            }

            # Prune stale auto-generated ClientIPAddress_* rules
            Write-Host "        Pruning stale ClientIPAddress_* rules..." -ForegroundColor DarkGray
            $allRules = az postgres flexible-server firewall-rule list `
                --resource-group $azRg --name $azServer -o json 2>$null | ConvertFrom-Json
            $staleRules = $allRules | Where-Object { $_.name -like "ClientIPAddress_*" } |
                Select-Object -ExpandProperty name
            foreach ($rule in $staleRules) {
                az postgres flexible-server firewall-rule delete `
                    --resource-group $azRg --name $azServer --rule-name $rule --yes 2>$null
                Write-Host "        Deleted: $rule" -ForegroundColor DarkGray
            }
        }
    }
}

Write-Host "[CHECK] Testing Azure DB connectivity (port 5432)..." -ForegroundColor Yellow
$dbHost = "lexmateph-ea-db.postgres.database.azure.com"
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $ar  = $tcp.BeginConnect($dbHost, 5432, $null, $null)
    if ($ar.AsyncWaitHandle.WaitOne(5000, $false) -and $tcp.Connected) {
        $tcp.EndConnect($ar); $tcp.Close()
        Write-Host "        [OK] Azure DB reachable." -ForegroundColor Green
    } else {
        $tcp.Close(); throw "timeout"
    }
} catch {
    Write-Host ""
    Write-Host "  !! AZURE DB UNREACHABLE after firewall update - check az login status" -ForegroundColor Red
    Write-Host "  !! Run: az login" -ForegroundColor Yellow
    Write-Host ""
}

# -- Helper: wait for a TCP port ----------------------------------------------
function Wait-Port {
    param([string]$Label, [int]$Port, [int]$MaxSec = 120)
    Write-Host "[WAIT] Polling $Label on port $Port ..." -ForegroundColor Yellow
    $elapsed = 0; $sleep = 1
    while ($elapsed -lt $MaxSec) {
        try {
            $p = New-Object System.Net.Sockets.TcpClient
            $a = $p.BeginConnect("127.0.0.1", $Port, $null, $null)
            if ($a.AsyncWaitHandle.WaitOne(400, $false) -and $p.Connected) {
                $p.EndConnect($a); $p.Close()
                Write-Host "       [OK] $Label is up." -ForegroundColor Green
                return $true
            }
            $p.Close()
        } catch {}
        Write-Host "       ... still waiting ($elapsed s)" -ForegroundColor DarkGray
        Start-Sleep -Seconds $sleep
        $elapsed += $sleep
        $sleep = [Math]::Min(6, [Math]::Ceiling($sleep * 1.5))
    }
    Write-Host "       [WARN] $Label did not respond in ${MaxSec}s - continuing anyway." -ForegroundColor DarkYellow
    return $false
}

# -- 1. Azure Functions API (:7071) -------------------------------------------
Write-Host "`n[START] Azure Functions API -> http://localhost:7071" -ForegroundColor Yellow
$apiBat = Join-Path $env:TEMP "lexmate_api.bat"
$apiBatContent = "@echo off`r`n"
$apiBatContent += "cd /d `"$apiDir`"`r`n"
$apiBatContent += "call .venv\Scripts\activate.bat`r`n"
$apiBatContent += "set DB_CONNECTION_STRING=`r`n"
$apiBatContent += "set ENVIRONMENT=`r`n"
$apiBatContent += "set PYTHONPATH=.`r`n"
$apiBatContent += "echo [API] Starting on http://localhost:7071 ...`r`n"
$apiBatContent += "func start`r`n"
Set-Content -Path $apiBat -Value $apiBatContent -Encoding ASCII
Start-Process cmd -ArgumentList "/k", "`"$apiBat`""
Wait-Port "Azure Functions" 7071

# -- 2. Vite frontend (:5173) -------------------------------------------------
Write-Host "`n[START] Vite frontend -> http://localhost:5173" -ForegroundColor Yellow
$viteBat = Join-Path $env:TEMP "lexmate_vite.bat"
$viteBatContent = "@echo off`r`n"
$viteBatContent += "cd /d `"$frontendDir`"`r`n"
$viteBatContent += "if not exist node_modules call npm install`r`n"
$viteBatContent += "echo [VITE] Starting on http://localhost:5173 ...`r`n"
$viteBatContent += "npm run dev -- --host 0.0.0.0`r`n"
Set-Content -Path $viteBat -Value $viteBatContent -Encoding ASCII
Start-Process cmd -ArgumentList "/k", "`"$viteBat`""
Wait-Port "Vite" 5173

# -- 3. SWA CLI emulator (:4280) ----------------------------------------------
$swaExists = Get-Command swa -ErrorAction SilentlyContinue
if (-not $swaExists) {
    Write-Host "`n[WARN] SWA CLI not found. Install: npm i -g @azure/static-web-apps-cli" -ForegroundColor Yellow
    Write-Host "       Use http://localhost:5173 directly." -ForegroundColor DarkGray
} else {
    Write-Host "`n[START] SWA CLI emulator -> http://localhost:4280" -ForegroundColor Yellow
    $swaBat = Join-Path $env:TEMP "lexmate_swa.bat"
    $swaBatContent = "@echo off`r`n"
    $swaBatContent += "cd /d `"$Root`"`r`n"
    $swaBatContent += "echo [SWA] Starting on http://localhost:4280 ...`r`n"
    $swaBatContent += "swa start --config-name bar-project-v2`r`n"
    Set-Content -Path $swaBat -Value $swaBatContent -Encoding ASCII
    Start-Process cmd -ArgumentList "/k", "`"$swaBat`""
}

# -- 4. Admin backend (:8000) -------------------------------------------------
if (Test-Path $adminVenvPython) {
    Write-Host "`n[START] Admin backend (FastAPI) -> http://localhost:8000" -ForegroundColor Yellow
    $adminApiBat = Join-Path $env:TEMP "lexmate_admin_api.bat"
    $adminApiBatContent = "@echo off`r`n"
    $adminApiBatContent += "cd /d `"$adminBackendDir`"`r`n"
    $adminApiBatContent += "echo [ADMIN API] Starting on http://localhost:8000 ...`r`n"
    $adminApiBatContent += "`"$adminVenvPython`" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`r`n"
    Set-Content -Path $adminApiBat -Value $adminApiBatContent -Encoding ASCII
    Start-Process cmd -ArgumentList "/k", "`"$adminApiBat`""
} else {
    Write-Host "`n[SKIP] Admin backend - venv not set up (see warnings above)." -ForegroundColor DarkGray
}

# -- 5. Admin frontend (:3000) ------------------------------------------------
Write-Host "`n[START] Admin frontend (Next.js) -> http://localhost:3000" -ForegroundColor Yellow
$adminFeBat = Join-Path $env:TEMP "lexmate_admin_fe.bat"
$adminFeBatContent = "@echo off`r`n"
$adminFeBatContent += "cd /d `"$adminFrontendDir`"`r`n"
$adminFeBatContent += "if not exist node_modules call npm install`r`n"
$adminFeBatContent += "echo [ADMIN FE] Starting on http://localhost:3000 ...`r`n"
$adminFeBatContent += "npm run dev`r`n"
Set-Content -Path $adminFeBat -Value $adminFeBatContent -Encoding ASCII
Start-Process cmd -ArgumentList "/k", "`"$adminFeBat`""

# -- Done ---------------------------------------------------------------------
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  All processes launched." -ForegroundColor Green
Write-Host ""
Write-Host "  Main app:   http://localhost:4280  (SWA - recommended)" -ForegroundColor Green
Write-Host "              http://localhost:5173  (Vite direct)" -ForegroundColor DarkGray
Write-Host "  Admin app:  http://localhost:3000  (Next.js)" -ForegroundColor Green
Write-Host "  Admin API:  http://localhost:8000  (FastAPI)" -ForegroundColor Green
Write-Host "  LAN:        http://$($localIp):4280" -ForegroundColor Green
Write-Host ""
Write-Host "  Close CMD windows or run restart_all.ps1 to stop." -ForegroundColor DarkGray
Write-Host "==========================================" -ForegroundColor Cyan
