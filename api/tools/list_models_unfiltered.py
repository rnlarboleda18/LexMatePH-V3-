import requests

API_KEY = "AIzaSyANtmAjiEpDZCXB-oDUwDOX0FvTKpjgIPk"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        with open("all_models.txt", "w", encoding="utf-8") as f:
            f.write(f"Total Models Found: {len(models)}\n")
            f.write("=== COMPLETE MODEL LIST ===\n")
            for m in models:
                f.write(f"- {m.get('name')}  |  ({m.get('displayName')})\n")
        print("Written to all_models.txt successfully.")
    else:
        print(f"Error {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
