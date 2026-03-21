import os
import psycopg2
from openai import OpenAI
import logging
import concurrent.futures
import re
import time
from psycopg2 import pool

# Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "REDACTED_OPENAI_KEY")
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [FACTS-OPENAI] %(message)s')

client = OpenAI(api_key=OPENAI_API_KEY)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 25, DB_CONNECTION_STRING)

def fix_facts_openai(cid, facts, full_text):
    context_text = full_text[:50000] if full_text else ""
    
    # EXACT SAME PROMPT as Gemini version
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
    
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a legal text formatting assistant. Follow instructions precisely."},
                {"role": "user", "content": prompt}
            ]
        )
        
        fixed_text = response.choices[0].message.content.strip()
        
        # Clean potential markdown fences
        fixed_text = re.sub(r'^```markdown\s*', '', fixed_text)
        fixed_text = re.sub(r'^```\s*', '', fixed_text)
        fixed_text = re.sub(r'\s*```$', '', fixed_text)
        
        return fixed_text
        
    except Exception as e:
        logging.error(f"Error CID {cid}: {e}")
        return None

def process_single_case(cid, facts, full_text):
    conn = None
    try:
        # Check if actually defective (Double check)
        is_blob = facts.count('\n\n') < 2
        has_pet = bool(re.search(r'\*\*.*(Petition|Appeal)', facts, re.IGNORECASE))
        
        if not is_blob and has_pet:
            return

        retries = 3
        while retries > 0:
            fixed_text = fix_facts_openai(cid, facts, full_text)
            
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
    conn = db_pool.getconn()
    cur = conn.cursor()
    
    print("[FACTS-OPENAI] Fetching Defective Cases...")
    
    # Same logic as Gemini version
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

    print(f"[FACTS-OPENAI] Found {len(defective_rows)} defective cases.")
    print("[FACTS-OPENAI] Launching 20-worker OpenAI fleet...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for row in defective_rows:
             cid, facts, ft = row
             futures.append(executor.submit(process_single_case, cid, facts, ft))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    mass_fix()
