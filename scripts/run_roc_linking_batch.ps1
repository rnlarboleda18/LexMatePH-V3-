# ROC Jurisprudence Linking Batch Runner (1997-2024)
# ===================================================

$startYear = 2014
$endYear = 1997
$workers = 10
$env:DB_CONNECTION_STRING = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

Write-Host "Starting ROC Batch Linking from $startYear to $endYear with $workers workers..." -ForegroundColor Cyan

for ($year = $startYear; $year -ge $endYear; $year--) {
    Write-Host "`n========================================================" -ForegroundColor Yellow
    Write-Host " PROCESSING YEAR: $year" -ForegroundColor Yellow
    Write-Host "========================================================" -ForegroundColor Yellow
    
    # Run the linker script for the specific year
    python scripts/universal_roc_linker.py --year $year --workers $workers --commit
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ Warning: Year $year finished with exit code $LASTEXITCODE" -ForegroundColor Red
    }
    
    Write-Host "Completed year $year. Taking a 5-second breather..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

Write-Host "`nAll years from $startYear to $endYear have been processed!" -ForegroundColor Green
