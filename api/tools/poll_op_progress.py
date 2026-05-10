"""Check import progress once."""
import requests, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

OP_ID = "7612634849882406912"
REGION = "europe-west4"
PROJECT = "gen-lang-client-0176283199"
url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/operations/{OP_ID}"

resp = requests.get(url, headers=_headers())
op = resp.json()
meta = op.get("metadata", {})
print("Done:", op.get("done", False))
print("Progress %:", meta.get("progressPercentage"))
print("Corpus ID:", meta.get("ragCorpusId"))
print("Config:", meta.get("importRagFilesConfig", {}).get("gcsSource", {}).get("uris", []))
