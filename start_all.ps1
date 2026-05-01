<#
  LexMatePH v3 - start local dev stack (cloud DB via api/local.settings.json).
  Order: Azure Functions (:7071) -> wait -> Vite (:5173) -> wait -> SWA (:4280)

  Bootstraps: Python .venv + pip, frontend npm deps, uses npx for func/swa if global CLIs missing.
  Requires: Node.js (LTS), Python 3.11+, api/local.settings.json — nothing else to run by hand.
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
$env:USE_LOCAL_POSTGRES = $null
$env:LOCAL_DB_CONNECTION_STRING = $null

# -- Paths --------------------------------------------------------------------
$apiDir           = Join-Path $Root "api"
$frontendDir      = Join-Path $Root "src\frontend"
$venvActivate     = Join-Path $apiDir ".venv\Scripts\activate.bat"
$localSettings    = Join-Path $apiDir "local.settings.json"

# -- Prerequisites ------------------------------------------------------------
if (-not (Test-Path $localSettings)) {
    Write-Host "[FATAL] Missing $localSettings" -ForegroundColor Red
    exit 1
}

# Timer triggers need AzureWebJobsStorage. Empty -> Functions tries Azurite on 127.0.0.1:10000.
# If AZURE_STORAGE_CONNECTION_STRING is set but AzureWebJobsStorage is blank, copy it into local.settings.json (backup first).
try {
    $lsObj = Get-Content $localSettings -Raw -Encoding UTF8 | ConvertFrom-Json
    $vals = $lsObj.Values
    if ($null -ne $vals) {
        $aw = [string]$vals.AzureWebJobsStorage
        $az = [string]$vals.AZURE_STORAGE_CONNECTION_STRING
        $awMissing = ($null -eq $aw -or [string]::IsNullOrWhiteSpace($aw))
        if ($awMissing -and $az -and -not [string]::IsNullOrWhiteSpace($az)) {
            $bak = "$localSettings.start_all.bak"
            Copy-Item -LiteralPath $localSettings -Destination $bak -Force -ErrorAction Stop
            $lsObj.Values.AzureWebJobsStorage = $az.Trim()
            $jsonOut = $lsObj | ConvertTo-Json -Depth 40
            [System.IO.File]::WriteAllText($localSettings, $jsonOut, [System.Text.UTF8Encoding]::new($false))
            Write-Host "[INFO] AzureWebJobsStorage was empty — copied from AZURE_STORAGE_CONNECTION_STRING (backup: $bak)." -ForegroundColor Green
        }
        elseif ($awMissing) {
            Write-Host "[WARN]  Set AzureWebJobsStorage or AZURE_STORAGE_CONNECTION_STRING in api\local.settings.json or timer triggers may fail." -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "[WARN]  Could not sync AzureWebJobsStorage in local.settings.json: $_" -ForegroundColor Yellow
}

# -- Toolchain (Node + Python) ------------------------------------------------
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[FATAL] Node.js not found. Install LTS from https://nodejs.org (needed for npm/npx, Vite, SWA)." -ForegroundColor Red
    exit 1
}

$pyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        $v = & python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($v -and [version]$v -ge [version]"3.10") { $pyCmd = "python" }
    } catch {}
}
if (-not $pyCmd -and (Get-Command py -ErrorAction SilentlyContinue)) {
    $pyCmd = "py"
}

if (-not $pyCmd) {
    Write-Host "[FATAL] Python 3.10+ not found. Install from https://www.python.org or use the py launcher." -ForegroundColor Red
    exit 1
}

# Create / refresh venv and install api/requirements.txt when needed
$venvPython = Join-Path $apiDir ".venv\Scripts\python.exe"
$requirements = Join-Path $apiDir "requirements.txt"
if (-not (Test-Path $venvPython)) {
    Write-Host "[BOOT] Creating Python venv in api\.venv ..." -ForegroundColor Yellow
    Push-Location $apiDir
    try {
        if ($pyCmd -eq "py") {
            & py -3 -m venv .venv
        } else {
            & python -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) { throw "venv exit $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
    if (-not (Test-Path $venvPython)) {
        Write-Host "[FATAL] Could not create api\.venv" -ForegroundColor Red
        exit 1
    }
    Write-Host "[BOOT] pip install -r api\requirements.txt (first run)..." -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
elseif ((Test-Path $requirements) -and ((Get-Item $requirements).LastWriteTime -gt (Get-Item $venvPython).LastWriteTime)) {
    Write-Host "[BOOT] requirements.txt changed — pip install ..." -ForegroundColor Yellow
    & $venvPython -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

if (-not (Test-Path $venvActivate)) {
    Write-Host "[FATAL] venv activate script missing: $venvActivate" -ForegroundColor Red
    exit 1
}

# Frontend deps when missing or lockfile newer than node_modules
$nmRoot = Join-Path $frontendDir "node_modules"
$lockFile = Join-Path $frontendDir "package-lock.json"
$needsNpm = -not (Test-Path $nmRoot)
$pkgJson = Join-Path $frontendDir "package.json"
if (-not $needsNpm -and (Test-Path $lockFile)) {
    if ((Get-Item $lockFile).LastWriteTime -gt (Get-Item $nmRoot).LastWriteTime) { $needsNpm = $true }
}
if (-not $needsNpm -and (Test-Path $pkgJson)) {
    if ((Get-Item $pkgJson).LastWriteTime -gt (Get-Item $nmRoot).LastWriteTime) { $needsNpm = $true }
}
if ($needsNpm) {
    Write-Host "[BOOT] npm install in src\frontend ..." -ForegroundColor Yellow
    Push-Location $frontendDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { exit 1 }
    } finally {
        Pop-Location
    }
}

# Prefer global CLIs if installed; otherwise npx (first run may download).
$funcStartLine = "npx --yes azure-functions-core-tools@4 start"
if (Get-Command func -ErrorAction SilentlyContinue) {
    $funcStartLine = "func start"
}
$swaStartLine = "npx --yes @azure/static-web-apps-cli start --config-name bar-project-v2"
if (Get-Command swa -ErrorAction SilentlyContinue) {
    $swaStartLine = "swa start --config-name bar-project-v2"
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
$apiBatContent += "$funcStartLine`r`n"
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

# -- 3. SWA CLI emulator (:4280) — npx so no global @azure/static-web-apps-cli install ----------
Write-Host "`n[START] SWA CLI emulator -> http://localhost:4280" -ForegroundColor Yellow
$swaBat = Join-Path $env:TEMP "lexmate_swa.bat"
$swaBatContent = "@echo off`r`n"
$swaBatContent += "cd /d `"$Root`"`r`n"
$swaBatContent += "echo [SWA] Starting on http://localhost:4280 ...`r`n"
$swaBatContent += "$swaStartLine`r`n"
Set-Content -Path $swaBat -Value $swaBatContent -Encoding ASCII
Start-Process cmd -ArgumentList "/k", "`"$swaBat`""
# First SWA run may download packages; allow extra time before the port opens.
Wait-Port "SWA emulator" 4280 240

# -- Done ---------------------------------------------------------------------
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  All processes launched." -ForegroundColor Green
Write-Host ""
Write-Host "  Main app:   http://localhost:4280  (SWA - recommended)" -ForegroundColor Green
Write-Host "              http://localhost:5173  (Vite direct)" -ForegroundColor DarkGray
Write-Host "  LAN:        http://$($localIp):4280" -ForegroundColor Green
Write-Host ""
Write-Host "  Close CMD windows or run restart_all.ps1 to stop." -ForegroundColor DarkGray
Write-Host "==========================================" -ForegroundColor Cyan
