"""Check embedding quota limits via Cloud Resource Manager API."""
import requests, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

PROJECT = "gen-lang-client-0176283199"
REGION = "europe-west4"

# Check quota via Service Usage API
url = f"https://serviceusage.googleapis.com/v1beta1/projects/{PROJECT}/services/aiplatform.googleapis.com/consumerQuotaMetrics"
resp = requests.get(url, headers=_headers())
print(f"Status: {resp.status_code}")
if resp.ok:
    data = resp.json()
    metrics = data.get("metrics", [])
    for m in metrics:
        if "textembedding" in m.get("metric", "").lower() or "prediction" in m.get("metric", "").lower():
            print(f"\nMetric: {m['metric']}")
            for limit_group in m.get("consumerQuotaLimits", []):
                print(f"  Limit: {limit_group.get('metric')} {limit_group.get('unit')}")
                for quota in limit_group.get("quotaBuckets", []):
                    print(f"    defaultLimit={quota.get('defaultLimit')}  effectiveLimit={quota.get('effectiveLimit')}")
else:
    print(resp.text[:300])
