
import os
import json
from google import genai
from pathlib import Path

def list_models():
    # Load settings
    settings_path = Path(__file__).resolve().parents[2] / "api" / "local.settings.json"
    api_key = None
    if settings_path.exists():
        with open(settings_path, 'r') as f:
            settings = json.load(f)
            api_key = settings.get("Values", {}).get("GEMINI_API_KEY") or settings.get("Values", {}).get("GOOGLE_API_KEY")

    if not api_key:
        print("Error: API Key not found in local.settings.json")
        return

    print(f"Using API Key: {api_key[:10]}...")
    
    try:
        client = genai.Client(api_key=api_key)
        
        print("\n--- Available Models ---")
        models = list(client.models.list())
        for model in models:
            # Safely print attributes
            name = getattr(model, 'name', 'N/A')
            display_name = getattr(model, 'display_name', 'N/A')
            print(f"Name: {name} ({display_name})")
            
        if not models:
            print("No models found or accessible.")

    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
