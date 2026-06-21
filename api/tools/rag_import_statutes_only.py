"""
Import statutes + remaining case batches after batch3 completes.
Logs to C:/Temp/rag_statutes_only.log
"""
import time, sys, os

os.makedirs("C:/Temp", exist_ok=True)

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    with open("C:/Temp/rag_statutes_only.log", "a") as f:
        f.write(line + "\n")

import vertexai
from vertexai.preview import rag
sys.path.insert(0, ".")

REGION  = "us-central1"
PROJECT = "gen-lang-client-0545071081"
CORPUS  = f"projects/{PROJECT}/locations/{REGION}/ragCorpora/6917529027641081856"

vertexai.init(project=PROJECT, location=REGION)

PREFIXES = [
    "gs://lexmateph-legal-corpus/statutes/provisions/",
    "gs://lexmateph-legal-corpus/cases/full-text-4/",
    "gs://lexmateph-legal-corpus/cases/full-text-5/",
    "gs://lexmateph-legal-corpus/cases/full-text-3/",   # last: split may still be in progress
]

def import_with_retry(path, max_wait_sec=28800):
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
            err = str(e)
            if "other operations running" in err or "VertexRagDataService requests" in err:
                log(f"  Busy, retrying in 60s...")
                time.sleep(60)
            elif "too many" in err.lower() or "10000" in err or "10,000" in err:
                log(f"  Too many files (split still in progress), retrying in 5min...")
                time.sleep(300)
            else:
                log(f"  FAILED: {e}")
                return False
    log("  TIMED OUT")
    return False

for path in PREFIXES:
    import_with_retry(path)
    time.sleep(15)

log("All done.")
