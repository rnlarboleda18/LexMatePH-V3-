import requests
import json

API_KEY = "REDACTED_API_KEY_HIDDEN"
# We need a valid file to post. We'll presume the last uploaded one works or upload a tiny one.
# Let's upload a tiny one first to be self-contained.

def upload_tiny():
    url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={API_KEY}"
    headers = {
        'X-Goog-Upload-Protocol': 'resumable',
        'X-Goog-Upload-Command': 'start',
        'X-Goog-Upload-Header-Content-Length': '10',
        'X-Goog-Upload-Header-Content-Type': 'application/json',
        'Content-Type': 'application/json'
    }
    # Initial request to get upload URL
    data = {"display_name": "tiny_test.jsonl"}
    r = requests.post(url, headers=headers, json=data)
    upload_url = r.headers.get("X-Goog-Upload-URL")
    
    # Upload bytes
    # Valid JSONL: {"request":...}
    content = b'{"request":{"model":"models/gemini-2.0-flash","content":{"parts":[{"text":"Hi"}]}}}'
    r2 = requests.post(upload_url, headers={'X-Goog-Upload-Command': 'upload, finalize'}, data=content)
    file_info = r2.json()
    return file_info['file']['name'] # files/xxxx

try:
    file_name = upload_tiny()
    print(f"Uploaded tiny file: {file_name}")
except Exception as e:
    print(f"Upload failed: {e}")
    file_name = "files/yqyojhivau1b" # Fallback to log's last file

print("-" * 20)

candidates = [
    f"https://generativelanguage.googleapis.com/v1beta/batches",
    f"https://generativelanguage.googleapis.com/v1beta/projects/-/batches",
    f"https://generativelanguage.googleapis.com/v1beta/locations/global/batches"
]

for base in candidates:
    url = f"{base}?key={API_KEY}"
    payload = {
        "src": file_name,
        "display_name": "debug_test"
    }
    print(f"POST {base} ...")
    r = requests.post(url, json=payload)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text}")
    print("-" * 20)
