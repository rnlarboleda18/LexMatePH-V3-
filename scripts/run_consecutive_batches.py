"""
run_consecutive_batches.py

Orchestrates running the decadal redigestion script consecutively for a specific number of batches.
"""

import subprocess
import sys
import time

def main():
    # We want to run consecutive batches until all pending ones are complete
    num_runs = 25
    print(f"============================================================")
    print(f"Starting consecutive redigestion run for {num_runs} batches...")
    print(f"Each run will execute 'scripts/redigest_flagged_decades.py --threads 5 --rpm 200'")
    print(f"With default 5 workers for Gemini and 10 workers for Grok.")
    print(f"============================================================")

    for run_idx in range(1, num_runs + 1):
        print(f"\n[ORCHESTRATOR] ---> Starting Batch Run {run_idx} of {num_runs} <---")
        start_time = time.monotonic()
        
        # Invoke the decadal script
        cmd = [sys.executable, "scripts/redigest_flagged_decades.py", "--threads", "5", "--rpm", "200"]
        print(f"[ORCHESTRATOR] Executing: {' '.join(cmd)}")
        
        # We run it with stdout/stderr passed directly so we see the live output
        res = subprocess.run(cmd)
        
        elapsed = time.monotonic() - start_time
        print(f"[ORCHESTRATOR] Batch Run {run_idx} finished in {elapsed:.2f} seconds with exit code {res.returncode}")
        
        if res.returncode != 0:
            print(f"[ORCHESTRATOR] ERROR: Batch Run {run_idx} failed. Aborting further runs.")
            sys.exit(res.returncode)

    print("\n============================================================")
    print("All 5 batches processed successfully!")
    print("============================================================")

if __name__ == "__main__":
    main()
