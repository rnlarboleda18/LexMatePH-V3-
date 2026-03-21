
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [LOW-ID] %(message)s')

# DB Pool (20 workers)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, DB_CONNECTION_STRING)

prompt_template = """
TASK: Determine the **Standard Short Title** (Strict 2023 SC Stylebook).
CONTEXT: We have titles corrupted with Artifacts (G.R. No), Aliases (aka), or Titles (Mr/Ms).
We need the **CLEAN PARTIES** only.

RULES:
1. **ARTIFACTS (G.R. No / Bar Exam)**:
   - If the current title is "G.R. No. 12345", you MUST read the TEXT and extract the real "Petitioner v. Respondent".
   - If it's a "Re: Bar Exam" formatting issue, standardise it.

2. **ALIASES / TITLES**:
   - **REMOVE**: "alias", "a.k.a.", "Mr.", "Ms.", "Mrs.".
   - *Bad*: "People v. Modesto Tee a.k.a. Estoy Tee" -> *Good*: "People v. Tee"
   - *Bad*: "Re: Letter of Mr. Octavio Kalalo" -> *Good*: "Re: Letter of Kalalo"

3. **INDIVIDUALS**:
   - Use **SURNAMES ONLY**.

4. **Format**: "[Petitioner] v. [Respondent]".
   - Keep "Re: ..." for administrative/bar matters if typically cited that way.

TEXT:
{text}

RETURN JSON:
{{
    "short_title": "..."
}}
"""


def fix_encoding(text):
    if not text: return text
    # Fix specific user complaints
    text = text.replace("Womenâ€™s", "Women's")
    try:
        fixed = text.encode('latin1').decode('utf-8')
        return fixed
    except:
        return text

def process_single_case(cid, text, model):
    conn = None
    try:
        header_text = text[:4000]
        
        # Retry logic
        retries = 3
        while retries > 0:
            try:
                response = model.generate_content(prompt_template.format(text=header_text), generation_config={"response_mime_type": "application/json"})
                break
            except Exception as e:
                if "429" in str(e):
                    time.sleep(2) # Increased sleep
                    retries -= 1
                else:
                    raise e
        
        if retries == 0:
            logging.error(f"Failed {cid} after retries (Rate Limit).")
            return

        data = json.loads(response.text)
        
        new_title = None
        # Handle case where AI returns a list [ { "short_title": ... } ]
        if isinstance(data, list):
            if len(data) > 0:
                if isinstance(data[0], dict):
                    new_title = data[0].get('short_title')
                elif isinstance(data[0], str):
                    new_title = data[0] # Just take the first string
            else:
                 logging.error(f"Unexpected JSON format for {cid}: {data}")
                 return
        elif isinstance(data, dict):
             new_title = data.get('short_title')
        
        if new_title:
            new_title = fix_encoding(new_title)
            conn = db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sc_decided_cases
                    SET short_title = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (new_title, cid))
                conn.commit()
            logging.info(f"Updated {cid}: {new_title}")
        
    except Exception as e:
        logging.error(f"Error {cid}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def mass_retitle():
    genai.configure(api_key=API_KEY)
    # User requested "Gemini 3 flash preview only"
    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
    except:
        logging.warning("Fallback/Error loading model")
        model = genai.GenerativeModel("gemini-2.0-flash")

    conn = db_pool.getconn()
    cur = conn.cursor()
    
    print("[ARTIFACT-FLEET] Fetching Target IDs (Artifacts & Aliases)...")
    # Target: G.R., Bar Exam, alias, a.k.a., Mr., Ms.
    cur.execute(r"SELECT id, full_text_md FROM sc_decided_cases WHERE short_title ~* 'G\.R\.|Bar Examination|alias|a\.k\.a\.|Mr\.|Ms\.' ORDER BY id ASC")
    rows = cur.fetchall()
    db_pool.putconn(conn)
    
    print(f"[ARTIFACT-FLEET] Loaded {len(rows)} cases to fix.")

    print("[ARTIFACT-FLEET] Launching 20-worker fleet...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for row in rows:
             cid, text = row
             futures.append(executor.submit(process_single_case, cid, text, model))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    mass_retitle()
