import google.generativeai as genai

API_KEY = "REDACTED_API_KEY_HIDDEN"
genai.configure(api_key=API_KEY)

with open('scripts/gemini_models.txt', 'w', encoding='utf-8') as f:
    f.write("Listing models...\n")
    try:
        for m in genai.list_models():
             f.write(f"Name: {m.name} | Methods: {m.supported_generation_methods}\n")
    except Exception as e:
        f.write(f"Error listing models: {e}\n")
