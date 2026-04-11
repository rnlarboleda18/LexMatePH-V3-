# One-time: registers Task Scheduler job to refresh Azure Postgres firewall hourly.
# Run in PowerShell (elevate only if Windows prompts for task registration).
$scriptPath = Join-Path $PSScriptRoot 'update-azure-postgres-firewall.ps1'
$arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" -ResourceGroup LexMatePH -ServerName lexmateph-ea-db"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName 'LexMatePH-AzurePostgresFirewall' -Action $action -Trigger $trigger -Settings $settings -Description 'Hourly: set Azure PostgreSQL dev-home-pc firewall rule to current public IP' -Force | Out-Null
Write-Host "Registered task: LexMatePH-AzurePostgresFirewall (runs every hour)."
