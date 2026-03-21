import requests

def invest_staging():
    live_url = "https://icy-pebble-07177fc03.2.azurestaticapps.net"
    
    # 1. Fetch a valid question ID from live list (try to get something)
    try:
        # Try both endpoints just in case
        q_resp = requests.get(f"{live_url}/api/questions?limit=5")
        if q_resp.status_code != 200:
            print(f"Failed to fetch from .2. URL. Status: {q_resp.status_code}")
            # Try fetching from the other URL just to GET an ID to use
            print("Trying fetching questions from main domain for ID reference...")
            q_resp = requests.get("https://icy-pebble-07177fc03.azurestaticapps.net/api/questions?limit=5")
            if q_resp.status_code != 200:
                 print(f"Failed both. Main gave: {q_resp.status_code}")
                 return
        
        questions = q_resp.json()
        valid_id = questions[0]['id']
        print(f"Using Question ID: {valid_id}")
        
    except Exception as e:
         print(f"Error: {e}")
         return

    # 2. Check headers
    audio_url = f"{live_url}/api/audio/question/{valid_id}"
    try:
         resp = requests.get(audio_url, allow_redirects=False)
         print(f"URL: {audio_url}")
         print(f"Status Code: {resp.status_code}")
         
         for k, v in resp.headers.items():
              print(f"  {k}: {v}")
              
         location = resp.headers.get("Location")
         if location:
              print(f"\nLocation Redirect: {location}")
              filename = location.split('/')[-1].split('?')[0]
              print(f"Inferred Cache File: {filename}")
              
    except Exception as e:
         print(f"Error checking audio: {e}")

if __name__ == "__main__":
    invest_staging()
