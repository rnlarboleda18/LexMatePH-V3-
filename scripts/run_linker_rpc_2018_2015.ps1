# RPC-only codal linker, decision years 2018 down to 2015 (one Vertex batch per year).
try { chcp 65001 | Out-Null } catch { }
$Host.UI.RawUI.WindowTitle = "LexMate linker RPC 2018-2015"
Set-Location $PSScriptRoot
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_GENAI_API_KEY -ErrorAction SilentlyContinue
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:GEMINI_LINKER_MODEL = "gemini-3-flash-preview"
if (-not $env:GEMINI_LINKER_HTTP_TIMEOUT_MS) { $env:GEMINI_LINKER_HTTP_TIMEOUT_MS = "300000" }
$log = Join-Path $PSScriptRoot "unified_linker_rpc_2018_2015.log"
foreach ($y in 2018, 2017, 2016, 2015) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "`n========== YEAR $y (RPC only, started $stamp) ==========`n"
    python -u unified_codal_linker.py --year $y --statutes RPC --workers 10 --commit 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host "`n========== ALL YEARS DONE (RPC 2018-2015) ==========`n"
