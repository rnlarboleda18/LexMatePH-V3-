import urllib.request
import re

def verify_live_bundle():
    url = "https://icy-pebble-07177fc03.2.azurestaticapps.net"
    print(f"Fetching: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        match = re.search(r'src="(/assets/index-[a-zA-Z0-9_-]+\.js)"', html)
        if match:
             bundle_url = url + match.group(1)
             print(f"Found Bundle URL: {bundle_url}")
             
             req_b = urllib.request.Request(bundle_url, headers={'User-Agent': 'Mozilla/5.0'})
             with urllib.request.urlopen(req_b) as response_b:
                  js_content = response_b.read().decode('utf-8')
                  
             if "text-amber-800" in js_content:
                  print("\n✅ MATCH FOUND: 'text-amber-800' EXISTS inside the live bundle!")
                  print("The layout styles ARE deployed on the live site.")
             else:
                  print("\n❌ MISSING: 'text-amber-800' was NOT found in the live bundle.")
        else:
             print("Could not find loaded JS bundle inside HTML file.")
             
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    verify_live_bundle()
