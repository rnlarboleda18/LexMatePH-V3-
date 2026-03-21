import requests

def invest_prod_direct():
    live_url = "https://icy-pebble-07177fc03.azurestaticapps.net"
    valid_id = 1678 # From staging test
    
    audio_url = f"{live_url}/api/audio/question/{valid_id}"
    try:
         # Use allow_redirects=False to inspect the Location header
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
         else:
              print("\nNo Location header found.")
              
    except Exception as e:
         print(f"Error checking audio: {e}")

if __name__ == "__main__":
    invest_prod_direct()
