"""
Wait for rag_import_statutes_batch3.py to finish (watches its log),
then launch rag_import_statutes_only.py automatically.
Logs to C:/Temp/launcher.log
"""
import time, os, subprocess, sys

LOG = "C:/Temp/rag_statutes.log"
LAUNCHER_LOG = "C:/Temp/launcher.log"

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    with open(LAUNCHER_LOG, "a") as f:
        f.write(line + "\n")

log("Waiting for batch3 script to complete (watching for 'All done.' in log)...")

deadline = time.time() + 36000  # 10 hours
while time.time() < deadline:
    try:
        with open(LOG, "r") as f:
            content = f.read()
        if "All done." in content:
            log("Batch3 script complete. Starting statutes import...")
            break
    except FileNotFoundError:
        pass
    time.sleep(30)
else:
    log("TIMEOUT waiting for batch3 — starting statutes import anyway")

# Give a small buffer then launch statutes import
time.sleep(10)

script_dir = os.path.dirname(os.path.abspath(__file__))
python = os.path.join(script_dir, "..", ".venv", "Scripts", "python.exe")
script = os.path.join(script_dir, "rag_import_statutes_only.py")

log(f"Launching: {python} {script}")
result = subprocess.run([python, script], capture_output=False)
log(f"Statutes import exited with code {result.returncode}")
