import urllib.request
import json

def test_endpoint():
    url = "http://localhost:7071/api/codex/versions?short_name=ROC"
    print(f"Testing URL: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            status = response.getcode()
            print(f"Status: {status}")
            data = response.read().decode('utf-8')
            print("Response Data (Truncated):")
            print(data[:500] + "...")
            json_data = json.loads(data)
            print(f"Articles Count: {len(json_data.get('articles', []))}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoint()
