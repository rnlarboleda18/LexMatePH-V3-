import os
import json
import psycopg2
import google.generativeai as genai
import logging
import concurrent.futures
import re
import time
from psycopg2 import pool

# Config
API_KEY = os.getenv("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [FACTS-FIX] %(message)s')
genai.configure(api_key=API_KEY)

# DB Pool (20 workers)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 25, DB_CONNECTION_STRING)

def fix_facts_smart(cid, facts, full_text, model):
    context_text = full_text[:50000] if full_text else ""
    
    prompt = f"""
    TASK: Fix the formatting and structure of the following Case Facts.
    
    CURRENT FACTS:
    {facts}
    
    FULL TEXT CONTEXT (Use ONLY if parts are missing):
    {context_text}...
    
    RULES:
    1. **Structure Requirement**: The Facts MUST be divided into exactly three sections with these headers:
       A. **The Antecedents**
       B. **Procedural History**
       C. **The Petition** (or **The Appeal**)
    
    2. **Formatting**: 
       - You MUST insert exactly TWO newline characters (`\\n\\n`) between each section.
       - Use bold headers: `**The Antecedents**`, etc.
    
    3. **STRATEGY (CRITICAL)**:
       - **SCENARIO A (Reformat Only)**: If the current text contains the information but is formatted as a single blob or has wrong headers, JUST REFORMAT IT. Split the paragraphs and add the correct headers. Do not rewrite the content if you don't have to.
       - **SCENARIO B (Missing Content)**: If a specific section (especially "The Petition" or "The Appeal") is **completely missing**, you MUST EXTRACT/REDIGEST that specific part from the `FULL TEXT CONTEXT`.
    
    4. **Safety**: Do not invent facts. If the full text doesn't contain the info, do not make it up.
    
    RETURN FORMAT:
    Return ONLY the fixed string (Markdown). Do NOT wrap in JSON. Just the text.
    """
    
    # Standard BLOCK_NONE settings
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        if "PROHIBITED_CONTENT" in str(e):
             logging.warning(f"CID {cid} BLOCKED (PROHIBITED_CONTENT). Skipping.")
             return "BLOCKED"
        logging.error(f"Error CID {cid}: {e}")
        return None

def process_single_case(cid, facts, full_text, model):
    conn = None
    try:
        # Check if actually defective (Double check)
        is_blob = facts.count('\n\n') < 2
        
        # Stricter double check for petition header
        has_pet = bool(re.search(r'\*\*.*(Petition|Appeal)', facts, re.IGNORECASE))
        
        if not is_blob and has_pet:
            return

        retries = 3
        while retries > 0:
            fixed_text = fix_facts_smart(cid, facts, full_text, model)
            
            if fixed_text == "BLOCKED":
                logging.warning(f"Skipping {cid} due to content block.")
                break # Exit retry loop, do not update DB
            
            if fixed_text:
                # Validation
                if "**The Antecedents" in fixed_text and ("**The Petition" in fixed_text or "**The Appeal" in fixed_text):
                     # SUCCESS
                     conn = db_pool.getconn()
                     with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE sc_decided_cases 
                            SET digest_facts = %s, updated_at = NOW() 
                            WHERE id = %s
                        """, (fixed_text, cid))
                        conn.commit()
                     logging.info(f"Fixed {cid}")
                     break
            
            retries -= 1
            if retries > 0: time.sleep(2)
            
    except Exception as e:
        logging.error(f"DB Error {cid}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def mass_fix():
    # User requested gemini-2.5-flash-lite
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
    except:
        model = genai.GenerativeModel("gemini-1.5-flash")

    conn = db_pool.getconn()
    cur = conn.cursor()
    
    print("[FACTS-FIX] Fetching Defective Cases...")
    
    # We fetch ALL and filter in Python because regex in SQL is messy for this specific blob logic
    # Or strict filter:
    cur.execute("SELECT id, digest_facts, full_text_md FROM sc_decided_cases WHERE digest_facts IS NOT NULL AND LENGTH(digest_facts) > 100")
    rows = cur.fetchall()
    db_pool.putconn(conn)
    
    defective_rows = []
    for row in rows:
        cid, facts, ft = row
        has_paragraphs = facts.count('\n\n') >= 2
        has_ants = bool(re.search(r'\*\*.*Antecedents', facts, re.IGNORECASE))
        has_proc = bool(re.search(r'\*\*.*Procedural History', facts, re.IGNORECASE))
        has_pet = bool(re.search(r'\*\*.*(Petition|Appeal)', facts, re.IGNORECASE))
        
        is_bad = False
        if not has_paragraphs: is_bad = True
        if not (has_ants and has_proc): is_bad = True
        if not has_pet: is_bad = True
        
        if is_bad:
            defective_rows.append(row)

    print(f"[FACTS-FIX] Found {len(defective_rows)} defective cases.")
    print("[FACTS-FIX] Launching 20-worker fleet...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for row in defective_rows:
             cid, facts, ft = row
             futures.append(executor.submit(process_single_case, cid, facts, ft, model))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    mass_fix()
