$ErrorActionPreference = "Stop"

# Configuration
$LOCAL_DB_URL = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
# The new hostname provided by the user
$TARGET_HOST = "bar-db-eu-west.postgres.database.azure.com"
$TARGET_USER = "bar_admin"
$TARGET_PASS = "[DB_PASSWORD]"
$TARGET_DB   = "postgres"

$DUMP_FILE = "C:\tmp\full_sync_dump.sql"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   FULL DB SYNC: Local -> EU West Azure" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# 1. Ensure tmp directory
if (-not (Test-Path "C:\tmp")) {
    New-Item -Path "C:\tmp" -ItemType Directory
}

# 2. Dump Local
Write-Host "`n[1/3] Dumping local database: bar_reviewer_local..." -ForegroundColor Yellow
$env:PGPASSWORD = "b66398241bfe483ba5b20ca5356a87be"
& pg_dump --no-owner --no-privileges --clean --if-exists --dbname=$LOCAL_DB_URL --file=$DUMP_FILE
if ($LASTEXITCODE -ne 0) { throw "Local dump failed" }

# 3. Restore to Azure
Write-Host "`n[2/3] Restoring to Azure: $TARGET_HOST..." -ForegroundColor Yellow
$env:PGPASSWORD = $TARGET_PASS
$TARGET_CONN_STRING = "postgresql://$($TARGET_USER)@$($TARGET_HOST):5432/$($TARGET_DB)?sslmode=require"

Write-Host "Connecting to target..."
& psql --dbname=$TARGET_CONN_STRING --file=$DUMP_FILE
if ($LASTEXITCODE -ne 0) { 
    Write-Host "`n[ERROR] Restore failed. This might be due to connection/auth or firewall." -ForegroundColor Red
    throw "Azure restore failed" 
}

# 4. Cleanup
Write-Host "`n[3/3] Cleaning up..." -ForegroundColor Yellow
if (Test-Path $DUMP_FILE) { Remove-Item $DUMP_FILE }

Write-Host "`n[SUCCESS] Full Database Sync Completed!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
