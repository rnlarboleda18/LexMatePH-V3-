import os
import json
import psycopg2
import google.generativeai as genai
import time
import logging
import argparse

API_KEY = "REDACTED_API_KEY_HIDDEN" 
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-2.0-flash')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SHORT-TITLE - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def process_batch(limit=20):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Select cases that HAVE digest but NO short_title
    query = """
        SELECT id, title, raw_content
        FROM supreme_decisions
        WHERE digest_facts IS NOT NULL 
          AND (short_title IS NULL OR short_title = '')
          AND raw_content IS NOT NULL
        LIMIT %s FOR UPDATE SKIP LOCKED
    """
    
    cur.execute(query, (limit,))
    cases = cur.fetchall()
    
    if not cases:
        conn.close()
        return 0
        
    logging.info(f"Processing {len(cases)} cases for Short Title generation...")
    
    for case in cases:
        cid, full_title, content = case
        
        # Optimize: Read only top part (Caption)
        # Assuming title caption is in first 2000 chars
        safe_content = content[:2000] if content else ""
        
        prompt = f"""
        You are a Legal Editor.
        Task: Create a **Short Title** for this Supreme Court case based on the Caption/Header.
        
        **Rules (Manual of Judicial Writing):**
        1. **General:** Petitioner v. Respondent (e.g. *Santos v. Cruz*).
        2. **Criminal:** People v. [Surname]. Drop "of the Philippines".
        3. **Government:** Use "Republic" or "Government" if party in civil case.
        4. **Compound Names:** Keep "De la Cruz", "Del Rosario", "San Miguel".
        5. **Corporations:** Use Full Name (Abbrev Inc./Corp. ok).
        6. **Public Officers:** Surname only (e.g. *City of Manila v. Subido*).
        7. **Consolidated:** Use Title of FIRST case only.
        8. **Special Proceedings:** "In re [Surname]".
        
        **Input:**
        Title field: {full_title}
        Caption Text: {safe_content}
        
        **Output:**
        Return ONLY a JSON: {{"short_title": "Result"}}
        """
        
        try:
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:-3].strip()
            elif text.startswith("```"): text = text[3:-3].strip()
            
            data = json.loads(text)
            st = data.get("short_title")
            
            if st:
                cur.execute("UPDATE supreme_decisions SET short_title = %s WHERE id = %s", (st, cid))
                conn.commit()
            else:
                logging.warning(f"No short title for ID {cid}")
            
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f"Error ID {cid}: {e}")
            conn.rollback()
            
    conn.close()
    return len(cases)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    
    logging.info("Starting Short Title Worker...")
    empty_streak = 0
    while True:
        try:
            count = process_batch(args.limit)
            if count == 0:
                empty_streak += 1
                if empty_streak > 5:
                    logging.info("No cases pending. Sleeping 30s...")
                    time.sleep(30)
                else:
                    time.sleep(5)
            else:
                empty_streak = 0
        except Exception as e:
            logging.error(f"Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
