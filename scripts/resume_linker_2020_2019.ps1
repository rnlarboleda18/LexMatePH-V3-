# Resume unified_codal_linker for 2020 then 2019 (RPC+RCC, skips cases already linked).
# Run from Explorer or: powershell -NoExit -ExecutionPolicy Bypass -File .\resume_linker_2020_2019.ps1
Set-Location $PSScriptRoot
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_GENAI_API_KEY -ErrorAction SilentlyContinue
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:GEMINI_LINKER_MODEL = "gemini-3-flash-preview"
# Per-request Vertex timeout (ms); prevents all workers blocking forever on a hung HTTP call
if (-not $env:GEMINI_LINKER_HTTP_TIMEOUT_MS) { $env:GEMINI_LINKER_HTTP_TIMEOUT_MS = "300000" }
$log = Join-Path $PSScriptRoot "unified_linker_resume_2020_2019.log"
foreach ($y in 2020, 2019) {
    Write-Host "`n========== YEAR $y ==========`n"
    python -u unified_codal_linker.py --year $y --workers 10 --commit 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host "`n========== ALL YEARS DONE ==========`n"
