import os
import json
import psycopg2
from google import genai
from google.genai import types
import time
import logging
import sys
import argparse

# Configuration
API_KEY = "REDACTED_API_KEY_HIDDEN"
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def fetch_content(conn, case_id):
    cur = conn.cursor()
    cur.execute("SELECT full_text_md FROM sc_decided_cases WHERE id = %s", (case_id,))
    row = cur.fetchone()
    if row:
        return row[0]
    return None

def fix_issues_ratio(target_file, model_name):
    with open(target_file, 'r') as f:
        target_ids = [line.strip() for line in f if line.strip()]
    
    logging.info(f"Loaded {len(target_ids)} cases to fix Issues/Ratio.")
    
    client = genai.Client(api_key=API_KEY)
    conn = get_db_connection()
    cur = conn.cursor()
    
    for case_id in target_ids:
        try:
            logging.info(f"Processing Case {case_id}...")
            content = fetch_content(conn, case_id)
            
            if not content:
                logging.warning(f"No content for {case_id}")
                continue
                
            safe_content = content[:150000]

            # PROMPT ADAPTED FROM MAIN DIGESTER
            prompt = f"""
            **ROLE:** Senior Legal Analyst.
            
            **TASK:** 
            Generate the "Issues" and "Ratio" sections for this Supreme Court decision.
            
            **STRICT FORMATTING RULES:**
            1. **ISSUES:** Provide a list of ALL issues using **BULLET POINTS**.
            2. **RATIO:** 
               - Address EVERY issue using a corresponding **BULLET POINT**. 
               - There must be a **1:1 CORRESPONDENCE** between the number of Issues bullets and Ratio bullets.
               - If there are 3 issues, there MUST be 3 ratio points.
            
            **CONTENT REQUIREMENTS:**
            - **Issues:** Phrased as questions (e.g., "Whether the...")
            - **Ratio:** 
              - **Reasoning:** For each issue, elaborate clearly on the Court's reasoning (Minimum 3-5 sentences per point).
              - **Citations:** Explicitly name referenced cases (e.g., "Applying *Tan-Andal*...").
            
            **INPUT TEXT:**
            {safe_content}
            
            **OUTPUT JSON:**
            {{
                "digest_issues": "* Whether...\\n* Whether...",
                "digest_ratio": "* On the first issue...\\n* On the second issue..."
            }}
            """
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.1,
                    safety_settings=[
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            )

            if not response.text:
                logging.error("Empty response")
                continue

            data = json.loads(response.text)
            if isinstance(data, list): data = data[0] if data else {}
            
            issues = data.get("digest_issues")
            ratio = data.get("digest_ratio")
            
            if issues and ratio:
                cur.execute("""
                    UPDATE sc_decided_cases 
                    SET digest_issues = %s, digest_ratio = %s, updated_at = NOW() 
                    WHERE id = %s
                """, (issues, ratio, case_id))
                conn.commit()
                logging.info(f"✅ Updated Issues/Ratio for {case_id}")
            else:
                logging.error(f"Missing fields in response for {case_id}")

        except Exception as e:
            logging.error(f"Error {case_id}: {e}")
            conn.rollback()
            time.sleep(1)
            
    conn.close()
    logging.info("Batch Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-file", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    
    fix_issues_ratio(args.target_file, args.model)
