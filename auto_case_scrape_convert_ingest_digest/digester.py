
import os
import google.genai as genai
from google.genai import types
import psycopg2
import json
import logging
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"
API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.5-flash-lite"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

DIGEST_PROMPT = """
You are a Senior Legal Editor and Bar Review Lecturer.
Digest the following Philippine Supreme Court decision.
Output strictly JSON.

JSON Structure:
{
    "title": "Clean Title",
    "case_number": "G.R. No. ...",
    "date": "YYYY-MM-DD",
    "ponente": "Justice Name",
    "digest_facts": "Concise facts...",
    "digest_issues": "Main legal issues...",
    "digest_ruling": "The court's decision...",
    "digest_ratio": "Step-by-step reasoning...",
    "digest_significance": "Why this case matters for the Bar Exam...",
    "keywords": ["tag1", "tag2"]
}

Case Content:
{case_text}
"""

def digest_one(case):
    case_id, content = case
    try:
        client = genai.Client(api_key=API_KEY)
        
        # Truncate content if massive (Gemini 2.5 has 1M context but good practice)
        prompt = DIGEST_PROMPT.format(case_text=content[:100000])
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF")] 
            )
        )
        
        return case_id, json.loads(response.text)
    except Exception as e:
        print(f"Error digesting {case_id}: {e}")
        return case_id, None

def run_digester():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Select cases with missing significance (indicator of undigested)
    # Limit to recently updated ones? Or just grab 10.
    cur.execute("""
        SELECT id, full_text_md 
        FROM sc_decided_cases 
        WHERE (digest_significance IS NULL OR digest_significance = '')
        AND full_text_md IS NOT NULL
        LIMIT 20
    """)
    cases = cur.fetchall()
    
    if not cases:
        logging.info("No undigested cases found.")
        return

    logging.info(f"Digesting {len(cases)} cases...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(digest_one, c): c[0] for c in cases}
        
        for future in futures:
            cid, result = future.result()
            if result:
                try:
                    cur.execute("""
                        UPDATE sc_decided_cases
                        SET digest_facts = %s,
                            digest_issues = %s,
                            digest_ruling = %s,
                            digest_ratio = %s,
                            digest_significance = %s,
                            ponente = %s,
                            keywords = %s,
                            ai_model = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (
                        result.get('digest_facts'),
                        result.get('digest_issues'),
                        result.get('digest_ruling'),
                        result.get('digest_ratio'),
                        result.get('digest_significance'),
                        result.get('ponente'),
                        json.dumps(result.get('keywords', [])),
                        MODEL_NAME,
                        cid
                    ))
                    conn.commit()
                    logging.info(f"✅ Digested Case ID {cid}")
                except Exception as db_err:
                    logging.error(f"DB Error saving {cid}: {db_err}")
                    conn.rollback()

    conn.close()

if __name__ == "__main__":
    run_digester()
