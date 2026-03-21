import subprocess
import csv
import io
import sys

def nuke_fleet():
    print("Obtaining process list...")
    # Get processes via PowerShell and emit as CSV for safe parsing
    ps_command = "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Select-Object ProcessId, CommandLine | ConvertTo-Csv -NoTypeInformation"
    
    try:
        output = subprocess.check_output(["powershell", "-Command", ps_command], stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
    except subprocess.CalledProcessError as e:
        print(f"Failed to query processes: {e.output.decode('utf-8', errors='ignore')}")
        return

    # Parse CSV
    f = io.StringIO(output)
    reader = csv.reader(f)
    
    targets = []
    
    for row in reader:
        if len(row) < 2: continue
        try:
            # Row headers might be "ProcessId", "CommandLine"
            # Or values. 
            pid_str = row[0]
            cmd_line = row[1]
            
            if not pid_str.isdigit(): continue
            
            # Check keywords
            if "generate_sc_digests_gemini.py" in cmd_line or "launch_finite_fleet.py" in cmd_line or "monitor_loop.py" in cmd_line:
                print(f"TARGET FOUND: PID {pid_str} | CMD: {cmd_line[:60]}...")
                targets.append(pid_str)
                
        except IndexError:
            continue

    if not targets:
        print("No fleet processes found running.")
        return

    print(f"Terminating {len(targets)} processes...")
    for pid in targets:
        try:
            subprocess.call(["taskkill", "/F", "/PID", pid])
            print(f"Killed {pid}")
        except Exception as e:
            print(f"Error killing {pid}: {e}")

if __name__ == "__main__":
    nuke_fleet()
