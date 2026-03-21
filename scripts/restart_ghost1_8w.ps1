# RESTART GHOST 1 ONLY
$ErrorActionPreference = "Stop"

function Launch-Fleet($tierLabel, $idFile, $model, $workerCount) {
    Write-Host "="*70 -ForegroundColor Cyan
    Write-Host "LAUNCHING $tierLabel FLEET ($workerCount Workers)" -ForegroundColor Cyan
    Write-Host "="*70 -ForegroundColor Cyan
    
    $ids = Get-Content $idFile
    $idsPerWorker = [Math]::Ceiling($ids.Count / $workerCount)
    
    for ($i = 0; $i -lt $workerCount; $i++) {
        $start = $i * $idsPerWorker
        $count = [Math]::Min($idsPerWorker, $ids.Count - $start)
        if ($count -le 0) { break }
        
        $workerFile = "worker_tier$($tierLabel[-1])_$($i+1).txt"
        $ids[$start..($start + $count - 1)] | Out-File $workerFile -Encoding utf8
        
        Start-Process python -ArgumentList "scripts/generate_sc_digests_gemini.py", "--target-ids-file", $workerFile, "--model", $model, "--force" -NoNewWindow
        Start-Sleep -Milliseconds 200
    }
}

Launch-Fleet "GHOST1" "ghost_tier_1.txt" "gemini-3-flash-preview" 8
