
import google.generativeai as genai

API_KEY = "REDACTED_API_KEY_HIDDEN"
genai.configure(api_key=API_KEY)

print(f"Listing models for key: {API_KEY[:10]}...")
print("-" * 40)

try:
    count = 0
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            count += 1
    
    if count == 0:
        print("No models found with generateContent capability.")
        
except Exception as e:
    print(f"Error: {e}")
