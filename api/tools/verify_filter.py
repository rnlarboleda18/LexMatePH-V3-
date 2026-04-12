import requests
import json

def verify_questions():
    url = "http://localhost:7071/api/lexify_questions?exam=political-pil"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            return

        data = response.json()
        questions = data.get("questions", [])
        
        print(f"Fetched {len(questions)} questions.")
        
        leakage_found = False
        for q in questions:
            text = q.get("text", "")
            # Check for patterns that should be filtered
            import re
            if re.search(r'\([a-d]\)', text, re.IGNORECASE) or re.search(r'\b[a-d]\.', text, re.IGNORECASE):
                print(f"LEAKAGE DETECTED in ID {q.get('id')}:")
                print(text[:200] + "...")
                leakage_found = True
        
        if not leakage_found:
            print("SUCCESS: No MCQs or sub-questions found in the response!")
            
    except Exception as e:
        print(f"Error calling API: {e}")

if __name__ == "__main__":
    verify_questions()
