import requests, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

OP_ID = "7612634849882406912"
REGION = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/operations/{OP_ID}"

resp = requests.get(url, headers=_headers())
op = resp.json()
r = op.get("response", {})
print(f"Imported: {r.get('importedRagFilesCount')}")
print(f"Failed:   {r.get('failedRagFilesCount')}")
