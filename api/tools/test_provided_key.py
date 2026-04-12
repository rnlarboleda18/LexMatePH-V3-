import google.generativeai as genai

def test():
    api_key = r"REDACTED_API_KEY_HIDDEN"
    print(f"Testing key: {api_key[:10]}...")
    genai.configure(api_key=api_key)
    
    try:
        print("Listing available models...")
        models = genai.list_models()
        available = [m.name for m in models]
        for name in available:
             print(f"- {name}")
             
        # Pick the latest flash
        # gemini 3.0 flash is not real, usually 2.0-flash or 1.5-flash
        target = 'gemini-1.5-flash'
        if any('2.0-flash' in m for m in available):
             target = 'gemini-2.0-flash'
        elif any('2.5-flash' in m for m in available): # just in case
             target = 'gemini-2.5-flash'
             
        print(f"\nUsing model: {target}")
        model = genai.GenerativeModel(target)
        response = model.generate_content("Hello! Verify connection code 104.")
        print(f"Success! Response: {response.text}")
        
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test()
