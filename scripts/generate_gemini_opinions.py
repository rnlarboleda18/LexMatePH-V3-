import os
import json
import psycopg2
import time
import argparse
import sys
from google import genai
from google.genai import types
from psycopg2.extras import register_default_jsonb, Json

# Configuration
API_KEY = os.getenv("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
MODEL_NAME = "gemini-2.0-flash-exp"

# Client
client = genai.Client(api_key=API_KEY)

def get_db_connection():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    register_default_jsonb(conn_or_curs=conn, globally=True)
    return conn

SYSTEM_PROMPT = """ROLE: You are a Legal Researcher.
GOAL: Extract SEPARATE OPINIONS from the Supreme Court Decision provided.
OUTPUT: Strict JSON Array of Objects.

SCHEMA:
[
  {
    "type": "Concurring" | "Dissenting" | "Concurring and Dissenting" | "Separate" | "Vote",
    "justice": "Justice Name",
    "summary": "2-3 sentence summary of their specific stance."
  }
]

INSTRUCTIONS:
1. Scan the text for separate opinions (usually at the very end).
2. If NO separate opinions exist, return empty array [].
3. Ignore the main Ponente.
4. Extract only: Concurring, Dissenting, Separate, or specific Votes explaining a position.
5. Be concise."""

def extract_opinions(full_text):
    try:
        # Optimization: Only send the last 30% of text if it's huge, as opinions are at the end.
        # But for correctness, let's send reasonably large chunk, biased to end.
        text_len = len(full_text)
        if text_len > 100000:
            # Take last 80k chars
             text_for_ai = "..." + full_text[-80000:]
        else:
            text_for_ai = full_text

        response = client.models.generate_content(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1
            ),
            contents=[text_for_ai]
        )
        
        return json.loads(response.text)
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-file", default="gemini_enbanc_opinions_ids.txt")
    args = parser.parse_args()

    # Load targets
    try:
        with open(args.target_file, 'r') as f:
            ids = [x.strip() for x in f.read().split(',') if x.strip()]
    except FileNotFoundError:
        print("Target file not found.")
        return

    print(f"Targeting {len(ids)} cases for Separate Opinion Backfill.")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    success_count = 0
    
    for case_id in ids:
        try:
            # Fetch
            cur.execute("SELECT full_text_md FROM sc_decided_cases WHERE id = %s", (case_id,))
            res = cur.fetchone()
            if not res or not res[0]:
                print(f"Case {case_id}: No text found.")
                continue
                
            full_text = res[0]
            
            # Generate
            # print(f"Processing {case_id}...")
            opinions_json = extract_opinions(full_text)
            
            if opinions_json is not None:
                # Update DB
                cur.execute(
                    "UPDATE sc_decided_cases SET separate_opinions = %s WHERE id = %s",
                    (Json(opinions_json), case_id)
                )
                conn.commit()
                print(f"Case {case_id}: Saved {len(opinions_json)} opinions.")
                success_count += 1
            else:
                print(f"Case {case_id}: Failed extraction.")
                
            # Rate limit slight
            time.sleep(0.5)
            
        except Exception as e:
            conn.rollback()
            print(f"Error on {case_id}: {e}")
            
    conn.close()
    print(f"Done. Processed {success_count} cases.")

if __name__ == "__main__":
    main()
