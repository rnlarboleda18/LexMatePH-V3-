import urllib.request
import urllib.error
import json

try:
    req = urllib.request.urlopen("http://localhost:7071/api/codex/versions?short_name=CONST")
    data = json.loads(req.read().decode('utf-8'))
    print("CONST OK, length:", len(data.get('articles', [])))

    req2 = urllib.request.urlopen("http://localhost:7071/api/codex/versions?short_name=FC")
    data2 = json.loads(req2.read().decode('utf-8'))
    print("FC OK, length:", len(data2.get('articles', [])))

except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
