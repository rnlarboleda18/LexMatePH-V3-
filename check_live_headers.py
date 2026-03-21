import requests

def check_headers():
    url = "https://icy-pebble-07177fc03.azurestaticapps.net/api/audio/question/1"
    try:
        # Use allow_redirects=False to see the headers from the redirector (Function App)
        resp = requests.get(url, allow_redirects=False)
        print(f"Status Code: {resp.status_code}")
        print("Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_headers()
