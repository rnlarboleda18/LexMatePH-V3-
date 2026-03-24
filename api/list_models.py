import requests

# Use the new key provided by the user
API_KEY = "AIzaSyANtmAjiEpDZCXB-oDUwDOX0FvTKpjgIPk"

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    print("Fetching available models...")
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        print("\n=== Available Models ===")
        for m in models:
            # We filter for flash-lite to find your exact match
            if "flash" in m.get("name", "").lower():
                print(f"- {m.get('name')}  ({m.get('displayName')})")
    else:
        print(f"Error {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"Connection failed: {e}")
