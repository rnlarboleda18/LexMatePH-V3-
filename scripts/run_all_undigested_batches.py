"""
run_all_undigested_batches.py

Orchestrates running the decadal redigestion script consecutively for all remaining undigested batches.
Streams output in real-time so that progress reports are visible immediately.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command_streaming(cmd):
    # Combined stdout and stderr to stream everything in real-time
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )
    
    output_lines = []
    for line in iter(process.stdout.readline, ''):
        try:
            sys.stdout.write(line)
            sys.stdout.flush()
        except UnicodeEncodeError:
            encoding = sys.stdout.encoding or 'utf-8'
            safe_line = line.encode(encoding, errors='replace').decode(encoding)
            sys.stdout.write(safe_line)
            sys.stdout.flush()
        output_lines.append(line)
        
    process.stdout.close()
    return_code = process.wait()
    full_output = "".join(output_lines)
    return return_code, full_output

def main():
    print("============================================================")
    print("Starting automatic consecutive orchestrator for ALL remaining batches...")
    print("Each run will execute 'scripts/redigest_flagged_decades.py --threads 5 --rpm 200'")
    print("Streaming output in real-time for live progress updates.")
    print("============================================================")

    run_idx = 1
    while True:
        print(f"\n[ORCHESTRATOR] ---> Starting Batch Run {run_idx} <---")
        start_time = time.monotonic()
        
        cmd = [sys.executable, "scripts/redigest_flagged_decades.py", "--threads", "5", "--rpm", "200"]
        print(f"[ORCHESTRATOR] Executing: {' '.join(cmd)}")
        
        ret_code, stdout_str = run_command_streaming(cmd)
        
        elapsed = time.monotonic() - start_time
        print(f"[ORCHESTRATOR] Batch Run {run_idx} finished in {elapsed:.2f} seconds with exit code {ret_code}")
        
        if ret_code != 0:
            print(f"[ORCHESTRATOR] ERROR: Batch Run {run_idx} failed with exit code {ret_code}. Aborting.")
            sys.exit(ret_code)
            
        if "batches completed." in stdout_str or "All batches completed." in stdout_str:
            print("[ORCHESTRATOR] SUCCESS: All batches have been processed!")
            break
            
        run_idx += 1
        time.sleep(2)

if __name__ == "__main__":
    main()
