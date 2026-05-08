"""
Import statutes + batch3 at 30 QPM (safe rate) after batch 2 completes.
Logs to C:/Temp/rag_statutes.log
"""
import time, sys, os

os.makedirs("C:/Temp", exist_ok=True)

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    try:
        with open("C:/Temp/rag_statutes.log", "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

import vertexai
from vertexai.preview import rag
sys.path.insert(0, ".")

REGION  = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
CORPUS  = f"projects/{PROJECT}/locations/{REGION}/ragCorpora/6917529027641081856"

vertexai.init(project=PROJECT, location=REGION)

PREFIXES = [
    "gs://lexmateph-legal-corpus/statutes/provisions/",
    "gs://lexmateph-legal-corpus/cases/full-text-3/",
]

def import_with_retry(path, max_wait_sec=14400):
    log(f"Importing {path} ...")
    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        try:
            result = rag.import_files(
                corpus_name=CORPUS,
                paths=[path],
                chunk_size=512,
                chunk_overlap=100,
                max_embedding_requests_per_min=30,
            )
            log(f"  OK: {result}")
            return True
        except Exception as e:
            if "other operations running" in str(e):
                log("  Op running, retrying in 60s...")
                time.sleep(60)
            else:
                log(f"  FAILED: {e}")
                return False
    log("  TIMED OUT")
    return False

for path in PREFIXES:
    import_with_retry(path)
    time.sleep(15)

log("All done.")
