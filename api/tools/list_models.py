import os
import sys

import requests

API_KEY = (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()
if not API_KEY:
    print("Set GOOGLE_API_KEY or GEMINI_API_KEY.", file=sys.stderr)
    sys.exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    print("Fetching available models...")
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        print("\n=== Available Models ===")
        for m in models:
            if "flash" in m.get("name", "").lower():
                print(f"- {m.get('name')}  ({m.get('displayName')})")
    else:
        print(f"Error {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"Connection failed: {e}")
