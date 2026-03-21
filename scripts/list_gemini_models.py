import google.generativeai as genai
import os

API_KEY = "REDACTED_API_KEY_HIDDEN"

def main():
    if not API_KEY or API_KEY == "YOUR_GOOGLE_API_KEY":
        print("Error: GOOGLE_API_KEY is not configured properly.")
        return

    print("Configuring Google GenerativeAI...")
    genai.configure(api_key=API_KEY)

    try:
        print("\n--- Available Gemini Models ---")
        for m in genai.list_models():
             supported_methods = ", ".join(m.supported_generation_methods)
             print(f"Name: {m.name}")
             print(f"  Display: {m.display_name}")
             print(f"  Methods: {supported_methods}")
             print("-" * 40)
             
    except Exception as e:
        print(f"Failed to list models: {e}")

if __name__ == "__main__":
    main()
