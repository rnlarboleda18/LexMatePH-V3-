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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [REPAIR] %(message)s')

# DB Pool (20 workers)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 25, DB_CONNECTION_STRING)

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
        fixed = text.encode('latin1').decode('utf-8')
        return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

def process_single_case(cid, text, model):
    conn = None
    try:
        header_text = text[:4000] 
        
        retries = 3
        while retries > 0:
            try:
                response = model.generate_content(prompt_template.format(text=header_text), generation_config={"response_mime_type": "application/json"})
                break
            except Exception as e:
                if "429" in str(e):
                    time.sleep(5)
                    retries -= 1
                else:
                    raise e
        
        if retries == 0:
            logging.error(f"Failed {cid} after retries (Rate Limit).")
            return

        data = json.loads(response.text)
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

def has_personal_honorific(title):
    """Detect personal honorifics (Judge Calimag) vs. institutional titles (Judge of First Instance)"""
    import re
    
    # Skip mojibake detection - that's still valid
    if 'Ã' in title or 'Â' in title:
        return True
    
    # Exclude institutional names that happen to contain keywords
    institutional_keywords = [
        'Social Justice Society',
        'Department of Justice',
        'Secretary of Justice',
        'Security and Sheriff',
        'Sheriff Division',
        'Justice For Children',
        'Justice International',
    ]
    
    for keyword in institutional_keywords:
        if keyword in title:
            return False
    
    # Pattern: Title followed by capitalized surname (likely personal honorific)
    # e.g., "Judge Calimag", "Justice Reyes", "Fiscal Santos"
    personal_patterns = [
        r'\bJudge\s+[A-Z][a-z]+\b',       # "Judge Calimag"
        r'\bJustice\s+[A-Z][a-z]+\b',    # "Justice Reyes"
        r'\bFiscal\s+[A-Z][a-z]+\b',     # "Fiscal Santos"
        r'\bSheriff\s+[A-Z][a-z]+\b',    # "Sheriff Cruz"
        r'\bGovernor\s+[A-Z][a-z]+\b',   # "Governor Lee"
        r'\bHon\.\s+[A-Z][a-z]+\b',      # "Hon. Torres"
        r'\bAtty\.\s+[A-Z][a-z]+\b',     # "Atty. Ramos"
    ]
    
    for pattern in personal_patterns:
        if re.search(pattern, title):
            return True
    
    return False

def mass_retitle():
    genai.configure(api_key=API_KEY)
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
    except:
        logging.warning("Fallback to 1.5-flash")
        model = genai.GenerativeModel("gemini-1.5-flash")

    conn = db_pool.getconn()
    cur = conn.cursor()
    
    print("[REPAIR] Fetching cases updated today...")
    # Fetch ALL cases updated today, filter in Python
    cur.execute("""
        SELECT id, short_title, full_text_md 
        FROM sc_decided_cases 
        WHERE updated_at >= DATE_TRUNC('day', NOW())
        ORDER BY id DESC
    """)
    all_rows = cur.fetchall()
    db_pool.putconn(conn)
    
    # Smart filtering
    target_rows = []
    for row in all_rows:
        cid, title, text = row
        if has_personal_honorific(title):
            target_rows.append(row)
    
    print(f"[REPAIR] Found {len(target_rows)} cases with personal honorifics (filtered from {len(all_rows)} total).")

    # 20 Workers (User Request)
    print("[REPAIR] Launching 20-worker fleet...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for row in target_rows:
             cid, title, text = row  # Unpack all 3 fields
             futures.append(executor.submit(process_single_case, cid, text, model))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    mass_retitle()
