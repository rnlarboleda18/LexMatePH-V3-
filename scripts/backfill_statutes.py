
import os
import json
import psycopg2
from google import genai
from google.genai import types
import logging
import sys
import time

# Configuration
API_KEY = os.getenv("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
MODEL_NAME = "gemini-2.0-flash"

# Safety: Allow processing of sensitive legal cases (e.g. Rape, Abuse)
SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
]

# Helper to clean JSON response
def clean_json_response(text):
    # Remove markdown code fences
    text = text.replace("```json", "").replace("```", "").strip()
    return text 

client = genai.Client(api_key=API_KEY, http_options={'timeout': 120000})

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [STATUTES] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

import argparse

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def run_backfill():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="Reprocess all cases")
    parser.add_argument("--worker-id", type=int, default=0, help="ID of this worker (0 to num_workers-1)")
    parser.add_argument("--num-workers", type=int, default=1, help="Total number of workers")
    parser.add_argument("--start-year", type=int, default=1900, help="Start year filter")
    parser.add_argument("--end-year", type=int, default=2100, help="End year filter")
    parser.add_argument("--descending", action="store_true", help="Process in descending ID order")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Base filtering
    # Base filtering: Only target NULL. Do not retry [] or 'null' as they are considered "Done/Empty".
    filter_condition = "(statutes_involved IS NULL)"
    if args.overwrite:
        filter_condition = "1=1" # Process everything

    # SHARDING + DATE FILTER + TYPE EXCLUSION
    # Order by ID to be deterministic with sharding
    order_direction = "DESC" if args.descending else "ASC"

    query = f"""
        SELECT id, full_text_md, short_title
        FROM sc_decided_cases 
        WHERE {filter_condition}
          AND full_text_md IS NOT NULL 
          AND LENGTH(full_text_md) > 100
          AND (updated_at IS NULL OR updated_at < NOW() - INTERVAL '5 minutes')
          AND (id % {args.num_workers} = {args.worker_id})
          AND (date >= '{args.start_year}-01-01' AND date <= '{args.end_year}-12-31')
          AND case_number NOT ILIKE 'A.M.%'
          AND case_number NOT ILIKE 'A.C.%'
          AND case_number NOT ILIKE 'U.D.K.%'
          AND case_number NOT ILIKE 'B.M.%'
          AND case_number NOT ILIKE 'IPC%'
          AND case_number NOT ILIKE 'OCA IPI%'
        ORDER BY id {order_direction}
        LIMIT 1
    """
    
    logging.info(f"Starting Statutes worker {args.worker_id}/{args.num_workers} ({args.start_year}-{args.end_year})...")
    
    while True:
        try:
            cur.execute(query)
            row = cur.fetchone()
            
            if not row:
                logging.info("No more cases found needing Statutes backfill.")
                # Wait a bit before retrying or exit? 
                # If we have many workers and they race, maybe wait and try again.
                # But 'SKIP LOCKED' usually returns None if everything locked.
                # Let's snooze and retry briefly, if still None, exit.
                time.sleep(2)
                cur.execute(query)
                if not cur.fetchone():
                    break
                continue
                
            case_id, text, title = row
            logging.info(f"Extracting Statutes for Case {case_id}: {title}")
            
            prompt = f"""
            **TASK:**
            Extract the "Statutes Involved" from the following Philippine Supreme Court decision.
            
            **INPUT TEXT:**
            {text} 

            **INSTRUCTIONS:**
            1. Identify **ALL** specific laws, codes, rules, or statutes cited (e.g., "Family Code", "Rules of Court", "Administrative Order No. 123", "Memorandum Circular").
            2. **Subject Matter Rules:** DEFINITELY INCLUDE any **Rules and Regulations** that are the specific subject matter of the case.
            3. **High Recall:** Include even if the citation is brief or the law is just mentioned.
            3. **Format:** extract the specific Article/Section if available, otherwise just the Law name.
            4. Limit to the **Top 15**.
            5. Return ONLY a JSON object with a single key "statutes_involved".
            
            **OUTPUT FORMAT:**
            {{
                "statutes_involved": [
                    {{"law": "Family Code", "provision": "Article 36"}},
                    {{"law": "Revised Penal Code", "provision": "Article 248"}}
                ]
            }}
            """
            
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.0,
                        safety_settings=SAFETY_SETTINGS
                    ),
                    # timeout removed
                )
                
                if response.text:
                    try:
                        cleaned_text = clean_json_response(response.text)
                        data = json.loads(cleaned_text, strict=False)
                        statutes = data.get('statutes_involved', [])
                        
                        logging.info(f"  > Found {len(statutes)} statutes.")
                        
                        # Update DB using SAME connection to clear lock
                        # Use clock_timestamp() because NOW() returns transaction start time
                        cur.execute(
                            "UPDATE sc_decided_cases SET statutes_involved = %s, updated_at = clock_timestamp() WHERE id = %s",
                            (json.dumps(statutes), case_id)
                        )
                        conn.commit() # Commit transaction, releasing lock

                    except json.JSONDecodeError as json_err:
                        logging.warning(f"  > JSON Error for {case_id}: {json_err}. Marking as processed to skip.")
                        cur.execute("UPDATE sc_decided_cases SET updated_at = clock_timestamp() WHERE id = %s", (case_id,))
                        conn.commit()

                else:
                    # Check for safety block
                    block_reason = "Unknown"
                    try:
                        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                            block_reason = response.prompt_feedback.block_reason
                    except:
                        pass

                    msg = f"BLOCKED: Case {case_id} Reason: {block_reason} -> MARKING AS EMPTY."
                    logging.warning(f"  > {msg}")
                    try:
                        with open("backfill_statutes_errors.log", "a") as f:
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
                    except: pass

                    cur.execute("UPDATE sc_decided_cases SET statutes_involved = '[]'::jsonb, updated_at = clock_timestamp() WHERE id = %s", (case_id,))
                    conn.commit()

            except Exception as e:
                logging.error(f"Error processing {case_id}: {e}")
                conn.rollback()
                
                # BUMP updated_at to prevent immediate retry loop
                try:
                    cur.execute("UPDATE sc_decided_cases SET updated_at = clock_timestamp() WHERE id = %s", (case_id,))
                    conn.commit()
                except Exception as update_err:
                    logging.error(f"Failed to bump updated_at for {case_id}: {update_err}")
                    conn.rollback()
                
                time.sleep(1)
                time.sleep(1)
        
        except Exception as e:
            logging.error(f"Loop error: {e}")
            conn.rollback()
            time.sleep(5)

if __name__ == "__main__":
    run_backfill()
