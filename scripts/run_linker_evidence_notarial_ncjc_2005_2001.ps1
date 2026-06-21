# Linker: Rules on Electronic Evidence, Rules on Notarial Practice, New Code of Judicial Conduct
# Decision years 2005 down to 2001 (descending). Uses Vertex AI (gemini-2.5-flash).
try { chcp 65001 | Out-Null } catch { }
$Host.UI.RawUI.WindowTitle = "LexMate linker Evidence+Notarial+NCJC 2005-2001"
Set-Location $PSScriptRoot
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:GEMINI_LINKER_HTTP_TIMEOUT_MS) { $env:GEMINI_LINKER_HTTP_TIMEOUT_MS = "300000" }
$log = Join-Path $PSScriptRoot "unified_linker_evidence_notarial_ncjc_2005_2001.log"
foreach ($y in 2005, 2004, 2003, 2002, 2001) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "`n========== YEAR $y (started $stamp) ==========`n"
    python -u unified_codal_linker.py --year $y --statutes AM-01-7-01-SC,AM-02-8-13-SC,NCJC --workers 5 --commit --vertex-project gen-lang-client-0545071081 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host "`n========== ALL YEARS DONE (Evidence + Notarial + NCJC 2005-2001) ==========`n"
