"""Poll a Vertex AI LRO until done."""
import requests, time, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

OP_ID = "7612634849882406912"
REGION = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/operations/{OP_ID}"

print(f"Polling: {url}")
while True:
    resp = requests.get(url, headers=_headers())
    if not resp.ok:
        print(f"Error {resp.status_code}: {resp.text[:200]}")
        break
    op = resp.json()
    done = op.get("done", False)
    metadata = op.get("metadata", {})
    stats = metadata.get("genericMetadata", metadata)
    print(f"done={done}  metadata keys={list(metadata.keys())[:5]}")
    if done:
        if "error" in op:
            print("FAILED:", op["error"])
        else:
            print("SUCCESS:", op.get("response", {}))
        break
    time.sleep(30)
