"""List available Gemini models via the REST API using the API key from local.settings.json."""
import json, requests
from pathlib import Path

settings = Path(__file__).resolve().parents[2] / "api" / "local.settings.json"
vals = json.loads(settings.read_text()).get("Values", {})
api_key = vals.get("GOOGLE_API_KEY") or vals.get("GEMINI_API_KEY")

if not api_key:
    raise SystemExit("No GOOGLE_API_KEY found in local.settings.json")

# Gemini Developer API  (generativelanguage.googleapis.com)
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=100"
resp = requests.get(url, timeout=15)
resp.raise_for_status()

models = resp.json().get("models", [])
gemini_models = sorted(
    [m for m in models if "gemini" in m.get("name", "").lower()],
    key=lambda m: m["name"]
)

print(f"{'Model ID':<50} {'Max Output Tokens':>18}  Input Tokens")
print("-" * 85)
for m in gemini_models:
    mid = m["name"].replace("models/", "")
    out = m.get("outputTokenLimit", "-")
    inp = m.get("inputTokenLimit", "-")
    print(f"{mid:<50} {str(out):>18}  {inp}")
