"""Poll the latest/specified operation."""
import requests, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

OP_ID = sys.argv[1] if len(sys.argv) > 1 else "1609618021574246400"
REGION = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/operations/{OP_ID}"

resp = requests.get(url, headers=_headers())
op = resp.json()
meta = op.get("metadata", {})
done = op.get("done", False)
print(f"Op: {OP_ID}")
print(f"Done: {done}")
if done:
    r = op.get("response", {})
    print(f"Imported: {r.get('importedRagFilesCount')}  Failed: {r.get('failedRagFilesCount')}")
    if "error" in op:
        print(f"Error: {op['error']}")
else:
    print(f"Progress: {meta.get('progressPercentage')}%")
    config = meta.get("importRagFilesConfig", {}).get("gcsSource", {}).get("uris", [])
    print(f"Config: {config}")
