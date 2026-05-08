"""
Import remaining GCS prefixes sequentially, retrying when an op is running.
Logs to C:/Temp/rag_import.log for monitoring.
"""
import time, sys, os

LOG = "C:/Temp/rag_import.log"
os.makedirs("C:/Temp", exist_ok=True)

def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

import vertexai
from vertexai.preview import rag

sys.path.insert(0, ".")

REGION  = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
CORPUS  = f"projects/{PROJECT}/locations/{REGION}/ragCorpora/6917529027641081856"

vertexai.init(project=PROJECT, location=REGION)

PREFIXES = [
    "gs://lexmateph-legal-corpus/cases/full-text-2/",
    "gs://lexmateph-legal-corpus/statutes/provisions/",
    "gs://lexmateph-legal-corpus/cases/full-text-3/",
]

def import_with_retry(path, max_wait_sec=7200):
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
            log(f"  SUCCESS: {result}")
            return True
        except Exception as e:
            if "other operations running" in str(e):
                log(f"  Op still running, retrying in 60s...")
                time.sleep(60)
            else:
                log(f"  FAILED: {e}")
                return False
    log(f"  TIMED OUT")
    return False

log("Starting sequential import of remaining prefixes...")
for path in PREFIXES:
    import_with_retry(path)
    time.sleep(15)
log("All done.")
