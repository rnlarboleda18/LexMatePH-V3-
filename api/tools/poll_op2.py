"""Check op 1609618021574246400 status."""
import requests, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

OP_ID = "1609618021574246400"
REGION = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/operations/{OP_ID}"

resp = requests.get(url, headers=_headers())
op = resp.json()
done = op.get("done", False)
print(f"Done: {done}")
if done:
    r = op.get("response", {})
    print(f"Imported: {r.get('importedRagFilesCount')}  Failed: {r.get('failedRagFilesCount')}")
else:
    print(f"Progress: {op.get('metadata', {}).get('progressPercentage')}%")
