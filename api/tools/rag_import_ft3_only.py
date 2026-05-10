"""Import ft3 only, with retry. Logs to C:/Temp/rag_ft3_only.log"""
import time, sys, os
os.makedirs("C:/Temp", exist_ok=True)

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    with open("C:/Temp/rag_ft3_only.log", "a") as f:
        f.write(line + "\n")

import vertexai
from vertexai.preview import rag
sys.path.insert(0, ".")

REGION  = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
CORPUS  = f"projects/{PROJECT}/locations/{REGION}/ragCorpora/6917529027641081856"

vertexai.init(project=PROJECT, location=REGION)

PATH = "gs://lexmateph-legal-corpus/cases/full-text-3/"
deadline = time.time() + 28800  # 8 hours

log(f"Importing {PATH} ...")
while time.time() < deadline:
    try:
        result = rag.import_files(
            corpus_name=CORPUS,
            paths=[PATH],
            chunk_size=512,
            chunk_overlap=100,
            max_embedding_requests_per_min=30,
        )
        log(f"  OK: {result}")
        break
    except Exception as e:
        err = str(e)
        if "other operations running" in err or "VertexRagDataService requests" in err:
            log(f"  Busy, retrying in 60s...")
            time.sleep(60)
        elif "too many" in err.lower() or "10000" in err or "10,000" in err:
            log(f"  Too many files, retrying in 5min...")
            time.sleep(300)
        elif "did not complete within" in err or "Operation timed out" in err:
            log(f"  SDK timeout — op submitted server-side.")
            break
        else:
            log(f"  FAILED: {e}")
            # transient network errors — retry after 30s
            time.sleep(30)
else:
    log("  TIMED OUT after 8h")

log("All done.")
