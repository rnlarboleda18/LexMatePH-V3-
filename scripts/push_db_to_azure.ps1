$ErrorActionPreference = "Stop"

$LOCAL_DB_URL = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
$AZURE_DB_URL = $env:AZURE_DB_CONNECTION_STRING
if (-not $AZURE_DB_URL) {
    $AZURE_DB_URL = Read-Host "Please enter the Azure Database Connection String (e.g. postgres://user:pass@host:port/db?sslmode=require)"
}
$DUMP_FILE = "C:\tmp\bar_reviewer_v2_dump.sql"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Database Migration: Local -> Azure" -ForegroundColor Cyan
==========================================

# Ensure tmp directory exists
if (-not (Test-Path "C:\tmp")) {
    New-Item -Path "C:\tmp" -ItemType Directory
}

Write-Host "`n[1/3] Dumping local database..." -ForegroundColor Yellow
$env:PGPASSWORD = "b66398241bfe483ba5b20ca5356a87be"
& pg_dump --no-owner --no-privileges --dbname=$LOCAL_DB_URL --file=$DUMP_FILE
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }

Write-Host "[2/3] Restoring to Azure Cloud..." -ForegroundColor Yellow
# PGPASSWORD should be set in the environment or extracted from the connection string.
& psql --dbname=$AZURE_DB_URL --file=$DUMP_FILE
if ($LASTEXITCODE -ne 0) { throw "psql restore failed" }

Write-Host "[3/3] Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item $DUMP_FILE

Write-Host "`n[SUCCESS] Migration completed successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
