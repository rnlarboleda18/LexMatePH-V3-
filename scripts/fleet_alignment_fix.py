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
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ALIGN-FIX] %(message)s')
genai.configure(api_key=API_KEY)

# DB Pool (20 workers)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 25, DB_CONNECTION_STRING)

def count_bullets(text):
    if not text: return 0
    return len(re.findall(r'^\s*([0-9]+\.|[\*\-])\s', text, re.MULTILINE))

def align_case_smart(cid, issues, ratio, full_text, model):
    context_text = full_text[:50000] if full_text else ""
    
    i_len = count_bullets(issues)
    r_len = count_bullets(ratio)
    target_len = max(i_len, r_len)

    prompt = f"""
    TASK: Reformat the Issues and Ratio decidendi to be STRICTLY 1:1 aligned.
    
    INPUT DATA:
    - Current Issues ({i_len}):
    {issues}
    
    - Current Ratio ({r_len}):
    {ratio}
    
    - Full Text Context:
    {context_text}...
    
    CRITICAL INSTRUCTIONS:
    1. **TARGET COUNT**: I have detected that the target number of bullet points is exactly **{target_len}**.
    2. **You MUST output exactly {target_len} Issue bullets and exactly {target_len} Ratio bullets.**
    
    3. **SCENARIO A: Issue Count < Ratio Count (Ratio={r_len}, Issue={i_len})** -> Target is {r_len}.
       - You MUST explode the Issues to match the Ratios.
       - Generate a specific **Issue Header** for every single orphan Ratio point.
       - Keep the Ratio text exactly as is.
    
    4. **SCENARIO B: Ratio Count < Issue Count (Ratio={r_len}, Issue={i_len})** -> Target is {i_len}.
       - You MUST extract or redigest the missing Ratios from the text to match the Issues.
       - If you cannot find the answer in the text, report "No ruling found" for that point, but keep the bullet count correct.
    
    5. **NO HALLUCINATIONS (CRITICAL)**: 
       - If a specific detail (date, justice, fact) is NOT found in the text, return null or skip it.
       - **Do NOT invent data.** 
       - If a missing Ratio cannot be found in the text, report "No ruling found" rather than fabricating one.
       - Use ONLY the provided text (Issues, Ratio, Full Text Context) as source.
    
    6. **FORMATTING**:
       - **Issues**: markdown bullet points (`* Issue 1...`).
       - **Ratio**: markdown bullet points (`* **On Issue 1:** ...`).
    
    RETURN JSON FORMAT:
    {{
        "issues": "* Issue 1...\\n* Issue 2... (Must have {target_len} items)",
        "ratio": "* **On Issue 1:** Ratio 1...\\n* **On Issue 2:** Ratio 2... (Must have {target_len} items)"
    }}
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return data.get('issues'), data.get('ratio')
    except Exception as e:
        logging.error(f"Error CID {cid}: {e}")
        return None, None

def process_single_case(cid, issues, ratio, full_text, model):
    conn = None
    try:
        retries = 3
        while retries > 0:
            new_i, new_r = align_case_smart(cid, issues, ratio, full_text, model)
            if new_i and new_r:
                # Basic validation
                if count_bullets(new_i) == count_bullets(new_r):
                    break
            retries -= 1
            if retries > 0: time.sleep(2)

        if new_i and new_r:
            conn = db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sc_decided_cases 
                    SET digest_issues = %s, digest_ratio = %s, updated_at = NOW() 
                    WHERE id = %s
                """, (new_i, new_r, cid))
                conn.commit()
            logging.info(f"Fixed {cid}: {count_bullets(new_i)} items")
        else:
             logging.warning(f"Failed to fix {cid}")
            
    except Exception as e:
        logging.error(f"DB Error {cid}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def mass_fix():
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
    except:
        model = genai.GenerativeModel("gemini-1.5-flash")

    conn = db_pool.getconn()
    cur = conn.cursor()
    
    print("[ALIGN-FIX] Fetching Misaligned Cases...")
    cur.execute("""
        SELECT id, digest_issues, digest_ratio, full_text_md
        FROM sc_decided_cases 
        WHERE digest_issues IS NOT NULL AND digest_ratio IS NOT NULL
        AND (
            (LENGTH(digest_issues) - LENGTH(REPLACE(digest_issues, '*', ''))) != 
            (LENGTH(digest_ratio) - LENGTH(REPLACE(digest_ratio, '*', '')))
        )
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    db_pool.putconn(conn)
    
    print(f"[ALIGN-FIX] Loaded {len(rows)} cases to align.")

    print("[ALIGN-FIX] Launching 30-worker fleet...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = []
        for row in rows:
             if len(row) == 4:
                 cid, issues, ratio, full_text = row
                 futures.append(executor.submit(process_single_case, cid, issues, ratio, full_text, model))
             else:
                 logging.warning("Row format unexpected")
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    mass_fix()
