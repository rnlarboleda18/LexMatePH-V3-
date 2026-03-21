
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
    # Escape unescaped control characters if strictly necessary, 
    # but usually stripping the fences is enough. 
    # Can also use a regex to fix unescaped newlines in strings if needed.
    return text 

client = genai.Client(api_key=API_KEY, http_options={'timeout': 120000})

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [CITATIONS] - %(levelname)s - %(message)s',
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
    parser.add_argument("--limit", type=int, default=1, help="Batch limit (internal loop)")
    parser.add_argument("--start-year", type=int, default=1900, help="Start year filter")
    parser.add_argument("--end-year", type=int, default=2100, help="End year filter")
    parser.add_argument("--descending", action="store_true", help="Process in descending ID order")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    # Base filtering
    # Base filtering: Only target NULL. Do not retry [] or 'null' as they are considered "Done/Empty".
    filter_condition = "(cited_cases IS NULL)"
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
    
    logging.info(f"Starting worker {args.worker_id}/{args.num_workers} ({args.start_year}-{args.end_year})...")
    
    while True:
        try:
            cur.execute(query)
            row = cur.fetchone()
            
            if not row:
                logging.info("No more cases found needing Citations backfill.")
                # Retry logic for concurrency race
                time.sleep(2)
                cur.execute(query)
                if not cur.fetchone():
                    break
                continue
                
            case_id, text, title = row
            logging.info(f"Extracting Citations for Case {case_id}: {title}")
            
            prompt = f"""
            **TASK:**
            Extract the "Cited Cases" (Jurisprudence) from the following Philippine Supreme Court decision.
            
            **INPUT TEXT:**
            {text} 

            **INSTRUCTIONS:**
            1. Identify Supreme Court cases cited in the text.
            2. **Classify the relationship:** "Applied" (used as precedent) or "Distinguished" (shown to be different).
            3. **Elaboration:** Provide a detailed explanation.
               - **Preferred:** 3 sentences (Doctrine, Application, Conclusion).
               - **Fallback:** If the citation is brief, a 1-2 sentence summary is acceptable. **DO NOT OMIT valid citations just because they lack deep elaboration.**
            4. **DEDUPLICATE CITATIONS:**
               - **Consolidate** multiple citations of the same case into a SINGLE entry.
               - If a case is cited for multiple points, combine them in the "Elaboration".
               - **DO NOT** list "Province of Sulu" and "Province of Sulu v. Medialdea" as separate entries.
            5. **Capture up to 15 most relevant** UNIQUE citations.
            6. **CITATION FORMAT (Strict):** 
               - **Mandatory:** "Case Name, G.R. No. XXXXX, Month DD, YYYY"
               - **Do NOT** use Phil. Reports or SCRA as the primary citation. **Always function G.R. No. and Date.**
               - Example: *People v. Estrada, G.R. No. 123456, December 25, 2025*
               - If G.R. No. is missing in the text, use Case Name + Date.
            
            **OUTPUT FORMAT:**
            {{
                "cited_cases": [
                    {{
                        "title": "People v. Macaraig, G.R. No. 123456, December 25, 2025", 
                        "relationship": "Applied",
                        "elaboration": "The Court established that positive identification prevails over the defense of denial and alibi. In this case, the prosecution witness positively identified the accused as the person who stabbed the victim, ensuring the identity was clear and unmistakable. Thus, the Court affirmed the conviction, ruling that the alibi could not stand against such specific positive identification."
                    }},
                    {{
                        "title": "Tan-Andal v. Andal, G.R. No. 196359, May 11, 2021", 
                        "relationship": "Distinguished", 
                        "elaboration": "This case modified the guidelines on psychological incapacity, establishing it as a legal rather than a medical concept. However, the current case involves a marriage declared void due to minority, not psychological incapacity. Therefore, the specific evidentiary standards set in Tan-Andal regarding psychological evaluation are not applicable to the facts at hand."
                    }}
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
                    # timeout removed, handled in client init
                )
                
                if response.text:
                    try:
                        cleaned_text = clean_json_response(response.text)
                        # strict=False allows control characters like newlines in strings
                        data = json.loads(cleaned_text, strict=False)
                        citations = data.get('cited_cases', [])
                        
                        # Filter limit in python to be safe
                        citations = citations[:15]
                        
                        logging.info(f"  > Found {len(citations)} citations.")
                        
                        # Update DB using SAME connection to clear lock
                        # Use clock_timestamp() because NOW() returns transaction start time,
                        # which is 5 mins old due to the API call delay.
                        cur.execute(
                            "UPDATE sc_decided_cases SET cited_cases = %s, updated_at = clock_timestamp() WHERE id = %s",
                            (json.dumps(citations), case_id)
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
                    
                    msg = f"BLOCKED: Case {case_id} Reason: {block_reason} -> MARKING AS EMPTY to stop retries."
                    logging.warning(f"  > {msg}")
                    try:
                        with open("backfill_errors.log", "a") as f:
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
                    except: pass

                    # MARK AS EMPTY [] to prevent infinite retry loop
                    cur.execute("UPDATE sc_decided_cases SET cited_cases = '[]'::jsonb, updated_at = clock_timestamp() WHERE id = %s", (case_id,))
                    conn.commit()

            except Exception as e:
                logging.error(f"Error processing {case_id}: {e}")
                try:
                    with open("backfill_errors.log", "a") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ERROR Case {case_id}: {e}\n")
                except: pass
                
                conn.rollback() # Release failed transaction
                
                # BUMP updated_at to prevent immediate retry loop
                try:
                    cur.execute("UPDATE sc_decided_cases SET updated_at = clock_timestamp() WHERE id = %s", (case_id,))
                    conn.commit()
                except Exception as update_err:
                    logging.error(f"Failed to bump updated_at for {case_id}: {update_err}")
                    conn.rollback()
                    
                time.sleep(1)
        
        except Exception as e:
            logging.error(f"Loop error: {e}")
            conn.rollback()
            time.sleep(5)

if __name__ == "__main__":
    run_backfill()
