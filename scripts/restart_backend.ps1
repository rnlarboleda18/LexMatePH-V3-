$env:DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
$env:GOOGLE_API_KEY = "REDACTED_API_KEY_HIDDEN"
$env:PYTHONPATH = "."

Set-Location "api"
$Wd = (Get-Location).Path
Write-Host "Starting Azure Functions Host in $Wd..."
$FuncPath = "C:\Users\rnlar\AppData\Roaming\npm\func.cmd"
Start-Process $FuncPath -ArgumentList "host", "start", "--verbose" -WorkingDirectory $Wd -RedirectStandardOutput "..\backend_log.txt" -RedirectStandardError "..\backend_err.txt" -NoNewWindow
