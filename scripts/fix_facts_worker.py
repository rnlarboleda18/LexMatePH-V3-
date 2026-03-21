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
API_KEY = "REDACTED_API_KEY_HIDDEN"  # Standardized Key
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
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

def fix_facts(target_file, model_name):
    # Read IDs
    with open(target_file, 'r') as f:
        target_ids = [line.strip() for line in f if line.strip()]
    
    logging.info(f"Loaded {len(target_ids)} cases to fix facts.")
    
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
                
            # Truncate if too long (manageable for facts)
            safe_content = content[:150000]

            prompt = f"""
            **ROLE:**
            Senior Reporter for the Supreme Court.
            
            **TASK:**
            Rewrite the "digest_facts" for this case. 
            
            **STRICT FORMATTING RULE:**
            The output MUST contain EXACTLY three (3) distinct paragraphs separated by double newlines (\\n\\n).
            The headers MUST be bolded exactly as follows:
            1. **The Antecedents**
            2. **Procedural History**
            3. **The Petition** (or **The Appeal**)

            **CONTENT GUIDELINES:**
            - **The Antecedents:** Summarize the underlying dispute/crimes.
            - **Procedural History:** Trace the case from lower courts/agencies to the current petition.
            - **The Petition/Appeal:** Describe the specific vehicle (e.g. Rule 45) and arguments raised to the SC.

            **INPUT TEXT:**
            {safe_content}

            **OUTPUT FORMAT (JSON):**
            {{
                "digest_facts": "**The Antecedents:** [Text...]\\n\\n**Procedural History:** [Text...]\\n\\n**The Petition:** [Text...]"
            }}
            """
            
            sys_instruction = "You are a Legal Editor enforcing strict structure."

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    temperature=0.1,
                    response_mime_type='application/json',
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
            if isinstance(data, list):
                data = data[0] if data else {}
            
            facts = data.get("digest_facts")
            
            if facts:
                # Update DB
                cur.execute("UPDATE sc_decided_cases SET digest_facts = %s, updated_at = NOW() WHERE id = %s", (facts, case_id))
                conn.commit()
                logging.info(f"✅ Updated Facts for {case_id}")
            else:
                logging.error(f"No digest_facts found in response for {case_id}")

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
    
    fix_facts(args.target_file, args.model)
