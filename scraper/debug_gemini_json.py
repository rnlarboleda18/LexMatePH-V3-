import os
import json
import logging
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash" 

def setup_client():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not found.")
    return genai.Client(api_key=API_KEY)

def debug_case(case_number="A.C. No. 102"):
    client = setup_client()
    prompt = f"""
    Verify the official promulgation date of the Philippine Supreme Court case: "{case_number}".
    
    ACTIONS:
    1. SEARCH the official Supreme Court E-Library (sc.judiciary.gov.ph), Lawphil, ChanRobles, or official reporter websites.
    2. FIND at least 3 distinct sources verifying the date.
    
    OUTPUT FORMAT (JSON ONLY):
    {{
      "promulgation_date": "YYYY-MM-DD" or null,
      "confidence": "High" or "Low",
      "sources": ["url1", "url2", "url3"],
      "reasoning": "Brief explanation of findings"
    }}
    
    If you cannot definitively find the date from reputable sources, return null for date.
    """
    
    print(f"Querying {MODEL_NAME} for {case_number}...")
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json"
            )
        )
        
        text = response.text
        print("\n--- RAW TEXT REPR ---")
        print(repr(text))
        print("--- END RAW TEXT ---")

        if not text:
             print("Text is empty.")
             if response.candidates:
                 print(f"Finish Reason: {response.candidates[0].finish_reason}")
             return

        print("\nAttempting JSON Parse...")
        try:
            data = json.loads(text)
            print("JSON Parse Success!")
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"JSON Parse Failed: {e}")
            
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    debug_case()
