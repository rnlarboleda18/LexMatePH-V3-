# Bar 2026 — sequential generation in specified order
# Run from api/ directory: .\run_bar_gen_all.ps1

$ErrorActionPreference = "Continue"
$apiDir  = $PSScriptRoot
$python  = "$apiDir\.venv\Scripts\python.exe"
$logDir  = "$apiDir\logs"
$script  = "tools\generate_bar_reviewer.py"
$subjects = @("remedial", "criminal", "civil", "labor", "commercial", "political")

foreach ($subj in $subjects) {
    $logFile = "$logDir\bar_gen_$subj.log"
    Write-Host ""
    Write-Host "========================================================"
    Write-Host "Starting: $subj  ($([datetime]::Now.ToString('yyyy-MM-dd HH:mm:ss')))"
    Write-Host "Log: $logFile"
    Write-Host "========================================================"

    & $python $script --subject $subj *> $logFile

    $exit = $LASTEXITCODE
    if ($exit -ne 0) {
        Write-Host "  WARNING: $subj exited with code $exit — check log for details"
    } else {
        Write-Host "  Done: $subj"
    }
}

Write-Host ""
Write-Host "All subjects complete. Review admin panel to publish drafts."
