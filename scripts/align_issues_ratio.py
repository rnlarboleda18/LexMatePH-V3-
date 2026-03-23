import os
import json
import psycopg2
from google import genai
from google.genai import types
import logging
import concurrent.futures

# Configuration
API_KEY = os.getenv("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
client = genai.Client(api_key=API_KEY)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def align_case(cid, issues, ratio):
    prompt = f"""
    TASK: Align the following legal Issues and Ratio decidendi for a Bar Review database.
    CURRENT STATE: The number of Issues ({len(issues.split('*'))-1}) does not match the number of Ratio points ({len(ratio.split('*'))-1}).
    
    ISSUES:
    {issues}
    
    RATIO:
    {ratio}
    
    INSTRUCTIONS:
    1. You MUST provide a 1:1 mapping between Issues and Ratio points.
    2. If there are more Ratio points than Issues, either combine related Ratio points or split the Issues to match.
    3. Ensure every Issue bullet point corresponds exactly to a Ratio bullet point.
    4. Keep the exact legal terminology and reasoning from the input.
    5. Output ONLY the fixed "issues" and "ratio" as JSON.
    
    RETURN JSON FORMAT:
    {{
        "issues": "* Fixed Issue 1\\n* Fixed Issue 2...",
        "ratio": "* **On Issue 1:** ...\\n* **On Issue 2:** ..."
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Fast & Cheap for this task
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type='application/json'
            )
        )
        data = json.loads(response.text)
        return data.get('issues'), data.get('ratio')
    except Exception as e:
        logging.error(f"Error CID {cid}: {e}")
        return None, None

def process_misalignments(worker_count=10):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Target cases with mismatch from audit logic
    logging.info("Fetching misaligned cases...")
    cur.execute("""
        SELECT id, digest_issues, digest_ratio 
        FROM sc_decided_cases 
        WHERE digest_issues IS NOT NULL AND digest_ratio IS NOT NULL
        AND (
            (LENGTH(digest_issues) - LENGTH(REPLACE(digest_issues, '*', ''))) != 
            (LENGTH(digest_ratio) - LENGTH(REPLACE(digest_ratio, '*', '')))
        )
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    
    logging.info(f"Loaded {len(rows)} cases for alignment.")

    def worker(row):
        cid, issues, ratio = row
        new_i, new_r = align_case(cid, issues, ratio)
        if new_i and new_r:
            try:
                # New connection per update for thread safety if not using pool
                conn_w = psycopg2.connect(DB_CONNECTION_STRING)
                cur_w = conn_w.cursor()
                cur_w.execute("""
                    UPDATE sc_decided_cases 
                    SET digest_issues = %s, digest_ratio = %s, updated_at = NOW() 
                    WHERE id = %s
                """, (new_i, new_r, cid))
                conn_w.commit()
                conn_w.close()
                logging.info(f"Fixed Case {cid}")
            except Exception as e:
                logging.error(f"Commit error Case {cid}: {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        executor.map(worker, rows)

if __name__ == "__main__":
    process_misalignments(worker_count=10)
