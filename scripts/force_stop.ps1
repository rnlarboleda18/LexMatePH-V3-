$log = "logs/stop.log"
"Starting Kill..." | Out-File $log

try {
    $processes = Get-WmiObject Win32_Process -Filter "Name = 'python.exe'"
    $count = 0
    
    foreach ($p in $processes) {
        $cmd = $p.CommandLine
        if ($cmd -match "finite_fleet" -or $cmd -match "generate_sc" -or $cmd -match "monitor_loop") {
            "Killing PID $($p.ProcessId): $cmd" | Out-File $log -Append
            try {
                $p.Terminate()
                "Terminated $($p.ProcessId)" | Out-File $log -Append
                $count++
            }
            catch {
                "Failed to kill $($p.ProcessId)" | Out-File $log -Append
            }
        }
    }
    "Total Killed: $count" | Out-File $log -Append
}
catch {
    "Error: $_" | Out-File $log -Append
}
