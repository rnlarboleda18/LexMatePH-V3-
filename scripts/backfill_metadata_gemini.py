import os
import json
import psycopg2
import google.generativeai as genai
import time
import logging

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
API_KEY = os.environ.get("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def process_metadata(target_ids):
    conn = get_db_connection()
import concurrent.futures

def process_single_case(cid, text, model, cur, conn):
    try:
        logging.info(f"Processing {cid}...")
        header_text = text[:10000] 
        response = model.generate_content(prompt_template.format(text=header_text), generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        
        # Update DB (Thread-safe cursor usage requires care, usually better to create cursor per thread or use pool, 
        # but for this script simpler to just get a fresh connection or rely on psycopg2 thread safety if configured)
        # Actually psycopg2 connections are thread safe but cursors are not shared safely usually.
        # Let's simple create a new short-lived cursor or connection per thread for safety.
        with get_db_connection() as thread_conn:
            with thread_conn.cursor() as thread_cur:
                thread_cur.execute("""
                    UPDATE sc_decided_cases
                    SET case_number = COALESCE(case_number, %s),
                        date = COALESCE(date, %s::date),
                        short_title = COALESCE(short_title, %s),
                        updated_at = NOW()
                    WHERE id = %s
                """, (data.get('case_number'), data.get('date'), data.get('short_title'), cid))
                thread_conn.commit()
        logging.info(f"Updated {cid}: {data}")
        
    except Exception as e:
        logging.error(f"Error {cid}: {e}")

prompt_template = """
EXTRACT METADATA from this legal text.
Return JSON:
{{ "case_number": "...", "date": "YYYY-MM-DD", "short_title": "..." }}
TEXT: {text}
"""

def process_metadata(target_ids):
    genai.configure(api_key=API_KEY)
    
    # User requested specifically: gemini-3-flash-preview
    model = genai.GenerativeModel("gemini-3-flash-preview")

    # Fetch Data first
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT id, full_text_md FROM sc_decided_cases WHERE id IN %s", (tuple(target_ids),))
    rows = cur.fetchall()
    conn.close()

    # Threaded Processing
    print(f"Backfilling {len(rows)} cases with 5 workers (Gemini 3 Flash Preview)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for row in rows:
             cid, text = row
             futures.append(executor.submit(process_single_case, cid, text, model, None, None))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-ids", required=True)
    args = parser.parse_args()
    ids = [int(x) for x in args.target_ids.split(',')]
    process_metadata(ids)
