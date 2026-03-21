import os
import json
import sys

# Add api folder to path to import blueprints
sys.path.insert(0, os.path.abspath('api'))

# Mocking modules that might fail due to missing dependencies not critical for this test
class MockBlueprint:
    def route(self, *args, **kwargs): return lambda f: f
import azure.functions as func
func.Blueprint = MockBlueprint

# Import the provider
from blueprints.audio_provider import _get_text_for_codal, audio_provider_bp

def test_lookup():
    # Load credentials for DB connection inside the script context if needed
    with open('api/local.settings.json', 'r') as f:
         config = json.load(f)
         os.environ["DB_CONNECTION_STRING"] = config.get('Values', {}).get('DB_CONNECTION_STRING')

    print("--- TESTING LOOKUP FOR I-0 (Article I) ---")
    try:
        text, title = _get_text_for_codal('I-0', 'const')
        print(f"Title Returned: {title}")
        print(f"Text Snippet: {text[:200] if text else 'None'}...")
        
    except Exception as e:
         print(f"Error: {e}")

    print("\n--- TESTING LOOKUP FOR II-0 (Article II) ---")
    try:
        text, title = _get_text_for_codal('II-0', 'const')
        print(f"Title Returned: {title}")
        print(f"Text Snippet: {text[:200] if text else 'None'}...")
        
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    test_lookup()
