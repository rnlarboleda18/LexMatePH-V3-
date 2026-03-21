import urllib.request
import json

try:
    url = "http://localhost:7071/api/roc/all"
    print(f"Calling HTTP: {url}")
    res = urllib.request.urlopen(url)
    data = res.read()
    json_data = json.loads(data)
    print(f"Success! Status: 200. Count: {len(json_data)}")
    print("\nLast 3 items:")
    for item in json_data[-3:]:
         print(f"  {item.get('article_num')}")
except Exception as e:
    print(f"HTTP Error: {e}")
