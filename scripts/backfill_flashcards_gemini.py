import os
import json
import psycopg2
import google.generativeai as genai
import logging
import concurrent.futures
import time
from psycopg2 import pool

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
API_KEY = os.environ.get("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# DB Pool (10 workers + spares)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, DB_CONNECTION_STRING)

prompt_template = """
TASK: Create 3-5 high-quality flashcards for this Philippine Supreme Court case.
AUDIENCE: Bar Exam Reviewers. Focus on the DOCTRINE, RULING, and KEY FACTS.
FORMAT: Return a JSON Array of objects. Each object must have "question" and "answer".

EXAMPLE:
[
  {{
    "question": "What is the doctrine of exhaustion of administrative remedies?",
    "answer": "It requires that where a remedy before an administrative body is provided by statute, relief must be sought in exhausting this remedy before the courts will act."
  }}
]

TEXT:
{text}

RETURN JSON ARRAY:
"""

def process_single_case(cid, text, model):
    conn = None
    try:
        # logging.info(f"Processing {cid}...")
        header_text = text[:8000] # Good context for flashcards
        
        # Retry logic for 429
        retries = 3
        while retries > 0:
            try:
                response = model.generate_content(prompt_template.format(text=header_text), generation_config={"response_mime_type": "application/json"})
                break
            except Exception as e:
                if "429" in str(e):
                    logging.warning(f"429 on {cid}, retrying...")
                    time.sleep(5)
                    retries -= 1
                else:
                    raise e
        
        if retries == 0:
            logging.error(f"Failed {cid} after retries (Rate Limit).")
            return

        json_text = response.text.strip()
        # Clean potential markdown fences
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.startswith("```"):
            json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]

        flashcards = json.loads(json_text)
        
        if flashcards and isinstance(flashcards, list):
            conn = db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sc_decided_cases
                    SET flashcards = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(flashcards), cid))
                conn.commit()
            logging.info(f"Updated {cid}: Generated {len(flashcards)} cards")
        
    except Exception as e:
        logging.error(f"Error {cid}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def backfill_flashcards():
    genai.configure(api_key=API_KEY)
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
    except:
        logging.warning("gemini-2.5-flash not found, falling back")
        model = genai.GenerativeModel("gemini-1.5-flash")

    conn = db_pool.getconn()
    cur = conn.cursor()
    
    print("Fetching Missing Flashcards...")
    cur.execute("""
        SELECT id, full_text_md 
        FROM sc_decided_cases 
        WHERE (flashcards IS NULL OR flashcards = '[]'::jsonb)
        AND full_text_md IS NOT NULL
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    db_pool.putconn(conn)
    
    print(f"Loaded {len(rows)} cases needing flashcards.")

    # 10 Workers
    print("Launching 10-worker Flashcard fleet...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for row in rows:
             cid, text = row
             futures.append(executor.submit(process_single_case, cid, text, model))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    backfill_flashcards()
