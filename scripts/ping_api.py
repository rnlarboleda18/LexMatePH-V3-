import requests

def main():
    url = "http://localhost:7071/api/questions"
    try:
        print(f"GET {url}...")
        resp = requests.get(url, params={"limit": 1})
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    main()
