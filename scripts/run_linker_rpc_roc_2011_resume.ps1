# Resume RPC + ROC linker for decision year 2011 (only cases with no RPC/ROC links are selected).
try { chcp 65001 | Out-Null } catch { }
$Host.UI.RawUI.WindowTitle = "LexMate linker RPC+ROC 2011 resume"
Set-Location $PSScriptRoot
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_GENAI_API_KEY -ErrorAction SilentlyContinue
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:GEMINI_LINKER_MODEL) { $env:GEMINI_LINKER_MODEL = "gemini-3-flash-preview" }
if (-not $env:GEMINI_LINKER_HTTP_TIMEOUT_MS) { $env:GEMINI_LINKER_HTTP_TIMEOUT_MS = "300000" }
$log = Join-Path $PSScriptRoot "unified_linker_rpc_roc_2011_resume.log"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "`n========== YEAR 2011 RESUME (RPC+ROC, started $stamp) ==========`n"
python -u unified_codal_linker.py --year 2011 --statutes "RPC,ROC" --workers 10 --commit 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "`n========== YEAR 2011 RESUME DONE ==========`n"
