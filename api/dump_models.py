import google.generativeai as genai

def dump():
    api_key = r"REDACTED_API_KEY_HIDDEN"
    genai.configure(api_key=api_key)
    
    try:
        models = genai.list_models()
        with open('api/available_models.txt', 'w') as f:
            for m in models:
                 # m.name is usually 'models/gemini-1.5-flash' etc.
                 f.write(f"{m.name}\n")
        print("Model names dumped to api/available_models.txt")
        
    except Exception as e:
         print(f"Error listing models: {e}")

if __name__ == "__main__":
    dump()
