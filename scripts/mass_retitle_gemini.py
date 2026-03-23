import os
import json
import psycopg2
import google.generativeai as genai
import logging
import concurrent.futures
import time
from psycopg2 import pool

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
API_KEY = os.environ.get("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# DB Pool (Better for 50 workers)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 60, DB_CONNECTION_STRING)

prompt_template = """
TASK: Extract a CONCISE Short Title for this case following the 2023 Supreme Court Stylebook.
RULES:
1. **NO 'et al.'**: Never use "et al.". Omit subsequent parties entirely.
2. **First Party Only**: Use only the first petitioner vs. the first respondent.
3. **Surnames/Agencies**: 
   - Individuals: Use surnames only (e.g., "Cruz v. Santos").
   - Agencies: Use the FULL official agency name (e.g., "Commissioner of Internal Revenue", "Social Security System"). 
     **CRITICAL**: Do NOT omit "Commissioner of" if it is part of the agency name (e.g. "Commissioner of Internal Revenue").
   - **Criminal Cases**: ALWAYS use "**People v. [Accused]**". Do NOT use "People of the Philippines".
4. **Correction**: Fix obvious OCR errors or garbled text in names if clear from context (e.g. "PETECISIONISSIONER" -> "Commissioner").
5. **Format**: "[First Petitioner] v. [First Respondent]"
6. **NO PROFESSIONAL TITLES (CRITICAL)**: Drop ALL titles, honorifics, and status indicators from the case name.
   - **REMOVE**: "Judge", "Ex-Judge", "Justice", "Presiding Judge", "Hon.", "Atty.", "Fiscal", "Sheriff", "Governor", etc.
   - **USE ONLY SURNAMES**.
   - Example High Priority: "Judge Asuncion v. Xxxx" -> "Asuncion v. Xxxx"
   - Example: "Heirs of Trazona v. Judge Calimag" -> "Heirs of Trazona v. Calimag"

TEXT:
{text}

RETURN JSON:
{{
    "short_title": "..."
}}
"""


def fix_encoding(text):
    if not text: return text
    try:
        # Attempt to reverse double-encoding (Latin1 -> UTF8)
        # e.g. "MuÃ±oz" (UTF-8 bytes interpreted as Latin-1) -> "Muñoz"
        fixed = text.encode('latin1').decode('utf-8')
        return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        # If it fails (e.g. valid UTF-8 that confuses latin1, or mixed), keep original
        return text

def process_single_case(cid, text, model):
    conn = None
    try:
        # logging.info(f"Processing {cid}...")
        header_text = text[:4000] # Shorter context to save tokens/time
        
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

        data = json.loads(response.text)
        new_title = data.get('short_title')
        
        # KEY FIX: Ensure no mojibake in the new title
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
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
    except:
        logging.warning("Fallback to 1.5-flash")
        model = genai.GenerativeModel("gemini-1.5-flash")

    conn = db_pool.getconn()
    cur = conn.cursor()
    
    # Exclude cases updated in last 6 hours (Already done) EXCEPT specifically targeted fixes
    print("Fetching Target IDs (prioritizing fixes)...")
    cur.execute("""
        SELECT id, full_text_md 
        FROM sc_decided_cases 
        WHERE (
            -- 1. High Priority: Recent Honorifics/Defects (Repair Job)
            short_title ILIKE '%Judge%' 
            OR short_title ILIKE '%Justice%' 
            OR short_title ILIKE '%Fiscal%'
            OR short_title ILIKE '%Sheriff%'
            OR short_title ILIKE '%Atty.%'
            OR short_title ILIKE '%Governor%'
            OR short_title ILIKE '%Hon.%'

            -- 2. Standard Low ID Backlog (Untouched > 6h)
            OR (updated_at < NOW() - INTERVAL '6 hours' OR updated_at IS NULL)
        )
        -- Removing global updated_at check to allow repairing recent defects
        ORDER BY 
            (short_title ILIKE '%Judge%') DESC,
            id ASC
    """)
    rows = cur.fetchall()
    db_pool.putconn(conn)
    
    print(f"Loaded {len(rows)} cases to fix.")

    # 20 Workers (User Request)
    print("Launching 20-worker fleet...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for row in rows:
             cid, text = row
             futures.append(executor.submit(process_single_case, cid, text, model))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    mass_retitle()
