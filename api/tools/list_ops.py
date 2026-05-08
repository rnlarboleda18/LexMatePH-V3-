"""List all operations on the RAG corpus."""
import requests, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

REGION = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
CORPUS_ID = "6917529027641081856"

url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/ragCorpora/{CORPUS_ID}/operations"

resp = requests.get(url, headers=_headers())
print(f"Status: {resp.status_code}")
if resp.ok:
    ops = resp.json().get("operations", [])
    print(f"Operations: {len(ops)}")
    for op in ops:
        done = op.get("done", False)
        meta = op.get("metadata", {})
        config = meta.get("importRagFilesConfig", {}).get("gcsSource", {}).get("uris", [])
        progress = meta.get("progressPercentage")
        name = op.get("name", "").split("/")[-1]
        print(f"  {name}: done={done} progress={progress}% config={config}")
        if done:
            r = op.get("response", {})
            print(f"    imported={r.get('importedRagFilesCount')} failed={r.get('failedRagFilesCount')}")
else:
    print(resp.text[:300])
