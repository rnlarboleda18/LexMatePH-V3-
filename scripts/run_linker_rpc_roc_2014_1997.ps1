# RPC + ROC codal linker: decision years 2014 down to 1997 (resume-safe per year).
try { chcp 65001 | Out-Null } catch { }
$Host.UI.RawUI.WindowTitle = "LexMate linker RPC+ROC 2014-1997"
Set-Location $PSScriptRoot
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_GENAI_API_KEY -ErrorAction SilentlyContinue
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:GEMINI_LINKER_MODEL = "gemini-3-flash-preview"
if (-not $env:GEMINI_LINKER_HTTP_TIMEOUT_MS) { $env:GEMINI_LINKER_HTTP_TIMEOUT_MS = "300000" }
$log = Join-Path $PSScriptRoot "unified_linker_rpc_roc_2014_1997.log"
for ($y = 2014; $y -ge 1997; $y--) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "`n========== YEAR $y (RPC+ROC, started $stamp) ==========`n"
    python -u unified_codal_linker.py --year $y --statutes "RPC,ROC" --workers 10 --commit 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host "`n========== ALL YEARS DONE (RPC+ROC 2014-1997) ==========`n"
