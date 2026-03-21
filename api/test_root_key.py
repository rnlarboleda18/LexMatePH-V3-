import google.generativeai as genai
import json

def test_key():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            api_key = settings['Values']['GOOGLE_API_KEY']
            
        print(f"Testing key starting with: {api_key[:10]}...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash') # Use flash for quick test
        
        response = model.generate_content("Hello! Are you there?")
        print("Success!")
        print(f"Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"Key failed: {e}")
        return False

if __name__ == "__main__":
    test_key()
