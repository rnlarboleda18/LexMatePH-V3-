import requests

def investigate_voice():
    live_url = "https://icy-pebble-07177fc03.azurestaticapps.net"
    
    # 1. Fetch a valid question ID
    try:
        q_resp = requests.get(f"{live_url}/api/questions?limit=5")
        if q_resp.status_code != 200:
            print(f"Failed to fetch questions. Status: {q_resp.status_code}")
            print(q_resp.text[:200])
            return
            
        questions = q_resp.json()
        if not questions:
            print("No questions returned from API")
            return
            
        valid_id = questions[0]['id']
        print(f"Found valid question ID: {valid_id}")
        
    except Exception as e:
        print(f"Error fetching questions: {e}")
        return

    # 2. Check audio headers
    audio_url = f"{live_url}/api/audio/question/{valid_id}"
    try:
        # Use allow_redirects=False to inspect the Location header
        resp = requests.get(audio_url, allow_redirects=False)
        print(f"Audio Start URL: {audio_url}")
        print(f"Status Code: {resp.status_code}")
        print("Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
            
        location = resp.headers.get("Location")
        if location:
            print(f"\nLocation Redirect: {location}")
            # Analyze location for the cache key name
            filename = location.split('/')[-1].split('?')[0]
            print(f"Inferred Cache File: {filename}")
            
    except Exception as e:
        print(f"Error checking audio: {e}")

if __name__ == "__main__":
    investigate_voice()
