import os
from google import genai

API_KEY = os.environ.get("GEMINI_API_KEY")

def list_models():
    client = genai.Client(api_key=API_KEY)
    print("Listing models...")
    for m in client.models.list():
        print(f"Name: {m.name} | Display: {m.display_name}")

if __name__ == "__main__":
    list_models()
