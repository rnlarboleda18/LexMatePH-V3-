
import os
import json
import psycopg2
import google.generativeai as genai
import time
import logging
import sys
import argparse
from psycopg2.extras import RealDictCursor
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configuration
API_KEY = "REDACTED_API_KEY_HIDDEN"
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

# Safety Settings
safety_settings = {
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

# Model Configuration
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash-lite'
model = genai.GenerativeModel(
    MODEL_NAME, 
    safety_settings=safety_settings,
    system_instruction="You are a legal research assistant. The following text is a Supreme Court case provided for academic legal analysis and bar exam preparation. Analyze the facts objectively and clinically. This request is for educational purposes only and does not intend to promote or describe violence for entertainment."
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def fetch_and_claim_case(limit=1, start_year=1901, end_year=1989, ascending=False):
    conn = get_db_connection()
    cur = conn.cursor()

    # Query for Legacy Cases
    order = "ASC" if ascending else "DESC"
    query = f"""
        SELECT id, full_text_md, title, case_number, date, ponente
        FROM sc_decided_cases
        WHERE 
            (date >= '{start_year}-01-01' AND date <= '{end_year}-12-31')
            AND (digest_significance != 'PROCESSING' OR digest_significance IS NULL)
            -- Target cases with missing facts (covering the "Metadata Only" holes)
            AND digest_facts IS NULL 
            -- Protect Gemini 3 work (Use %% for literal %)
            AND (ai_model NOT LIKE '%%gemini-3%%' OR ai_model IS NULL)
            AND full_text_md IS NOT NULL
        ORDER BY date {order}
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """
    
    try:
        cur.execute(query) # No params to avoid psycopg2 % escaping issues
        rows = cur.fetchall()
        
        if not rows:
            conn.close()
            return None

        cases = []
        for row in rows:
            try:
                # Debug logging
                # logging.info(f"Row len: {len(row)}")
                if len(row) < 6:
                     logging.error(f"Row too short: {len(row)} - {row}")
                     continue
                     
                case_id = row[0]
                # Mark as PROCESSING
                cur.execute("UPDATE sc_decided_cases SET digest_significance = 'PROCESSING' WHERE id = %s", (case_id,))
                
                full_text = row[1]
                # Safe unpacking
                cases.append((case_id, full_text, row[2], row[3], row[4], row[5])) 
            except Exception as e:
                logging.error(f"Row unpacking error: {e} - Row: {row}")
                continue

        conn.commit()
        conn.close()
        
        if limit == 1 and cases:
             return cases[0]
        return cases

    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        conn.close()
        return None

def generate_legacy_digest(case_id, full_text):
    # Prompt excludes Ratio and Significance
    prompt = f"""
    Analyze the following Philippine Supreme Court decision and provide a structured digest.
    
    **Instructions:**
    1.  **Facts:** detailed summary of the events leading to the case.
    2.  **Issues:** The legal questions resolved by the court.
    3.  **Ruling:** The court's decision and the legal basis for it.
    4.  **Ratio Decidendi:** The core principle or rule of law established.
    5.  **Significance:** Why this case is important (e.g., Landmark, Reiteration).
    
    **Strict Output Format:** JSON
    {{
        "digest_facts": "Markdown string...",
        "digest_issues": "Markdown string...",
        "digest_ruling": "Markdown string...",
        "digest_ratio": "Markdown string...",
        "digest_significance": "Markdown string...",
        "significance_category": "LANDMARK | DOCTRINAL | REITERATION"
    }}

    **Case Text:**
    {full_text[:100000]} 
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        # Check block reason
        if response.prompt_feedback.block_reason:
            logging.warning(f"Case {case_id} blocked: {response.prompt_feedback.block_reason}")
            return None

        return json.loads(response.text)
    except Exception as e:
        logging.error(f"AI Generation Error Case {case_id}: {e}")
        if "429" in str(e) or "Quota" in str(e):
             raise e # Rethrow for backoff
        return None

def save_digest(case_id, data):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE sc_decided_cases
            SET 
                digest_facts = %s,
                digest_issues = %s,
                digest_ruling = %s,
                digest_ratio = %s,
                digest_significance = %s,
                significance_category = %s,
                ai_model = %s
            WHERE id = %s
        """, (
            data.get('digest_facts'),
            data.get('digest_issues'),
            data.get('digest_ruling'),
            data.get('digest_ratio'),
            data.get('digest_significance'),
            data.get('significance_category'),
            MODEL_NAME,
            case_id
        ))
        conn.commit()
        logging.info(f"Saved Case ID {case_id}")
    except Exception as e:
        logging.error(f"Save Error Case {case_id}: {e}")
    finally:
        conn.close()

def reset_lock(case_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sc_decided_cases SET digest_significance = NULL WHERE id = %s AND digest_significance = 'PROCESSING'", (case_id,))
        conn.commit()
        conn.close()
        logging.info(f"Reset lock for Case ID {case_id}")
    except:
        pass

def worker_loop(start_year, end_year, ascending):
    while True:
        try:
            case = fetch_and_claim_case(limit=1, start_year=start_year, end_year=end_year, ascending=ascending)
            if not case:
                logging.info("No more cases found. Sleeping...")
                time.sleep(10)
                continue
                
            case_id, full_text = case[0], case[1]
            logging.info(f"Processing Case ID {case_id}...")
            
            data = generate_legacy_digest(case_id, full_text)
            
            if data:
                save_digest(case_id, data)
            else:
                 reset_lock(case_id)
                 
        except Exception as e:
             logging.error(f"Worker Loop Error: {e}")
             if "429" in str(e) or "Quota" in str(e):
                 logging.warning("Quota Exceeded. Sleeping 30s...")
                 time.sleep(30)
             time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=1901)
    parser.add_argument("--end-year", type=int, default=1989)
    parser.add_argument("--ascending", action="store_true")
    args = parser.parse_args()
    
    worker_loop(args.start_year, args.end_year, args.ascending)
