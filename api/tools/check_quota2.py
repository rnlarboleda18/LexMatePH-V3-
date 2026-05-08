"""Check textembedding-gecko quota specifically."""
import requests, sys
sys.path.insert(0, ".")
from brain.rag.corpus import _headers

PROJECT = "gen-lang-client-0176283199"
url = f"https://serviceusage.googleapis.com/v1beta1/projects/{PROJECT}/services/aiplatform.googleapis.com/consumerQuotaMetrics"

resp = requests.get(url, headers=_headers())
data = resp.json()
metrics = data.get("metrics", [])

# Find online_prediction_requests
for m in metrics:
    metric = m.get("metric", "")
    if "online_prediction" in metric:
        print(f"\nMetric: {metric}")
        for limit_group in m.get("consumerQuotaLimits", []):
            unit = limit_group.get("unit", "")
            for bucket in limit_group.get("quotaBuckets", []):
                print(f"  unit={unit} default={bucket.get('defaultLimit')} effective={bucket.get('effectiveLimit')}")
                dims = bucket.get("dimensions", {})
                if dims:
                    print(f"  dims={dims}")
