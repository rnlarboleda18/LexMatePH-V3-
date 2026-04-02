

import os
import json
import psycopg2
from google import genai
from datetime import datetime
import time

# Configure Gemini
try:
    with open('local.settings.json') as f:
        settings = json.load(f)
        # Fallback key (should be in settings, but for robustness)
        API_KEY = "REDACTED_API_KEY_HIDDEN"
except:
    API_KEY = "REDACTED_API_KEY_HIDDEN"

# Initialize Client
client = genai.Client(api_key=API_KEY)

def get_db_connection():
    conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def generate_description(current_text, old_text, amendment_id, prior_amendment_id, prior_date):
    retries = 0
    max_retries = 5
    base_delay = 2
    
    while retries < max_retries:
        try:
            prompt = f"""Compare the BEFORE and AFTER versions of this Philippine legal article amended by {amendment_id}.
            
            BEFORE (Governed by {prior_amendment_id}, effective {prior_date}):
            {old_text}
            
            AFTER (Amended by {amendment_id}):
            {current_text}
            
            Task: Write a DETAILED description of the changes (aim for 3-5 sentences).
            1. **History**: Mention what law is being amended/replaced. If it was the original 1932 RPC (Act No. 3815), mention that it is updating an old provision.
            2. **Specifics**: Detail the exact changes (e.g. "raised fine from X to Y").
            3. **Implications**: Explain the legal effect (e.g. "This effectively decriminalizes...", "This reclassifies the offense...").
            
            Structure the response as a coherent paragraph. DO NOT start or end with quotation marks.
            """
            
            response = client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            if "429" in str(e):
                delay = base_delay * (2 ** retries)
                print(f"    [!] Rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            else:
                print(f"Error generating description: {e}")
                return None
    return None

def test_describer():
    """Test the description generator"""
    print("\nTesting Description Generator (Gemini 3 Pro)...")
    print("=" * 60)
    
    current = "ART. 123. New text here."
    old = "ART. 123. Old text here."
    
    desc = generate_description(current, old, "TEST_AMENDMENT", "OLD_LAW", "1932-01-01")
    
    if desc:
        print("✓ SUCCESS")
        print(f"Generated Description: {desc}")
    else:
        print("✗ FAILED")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_describer()
    else:
        backfill_descriptions()
