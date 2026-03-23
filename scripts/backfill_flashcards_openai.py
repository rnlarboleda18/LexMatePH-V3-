import os
import json
import psycopg2
from openai import OpenAI
import logging
import concurrent.futures
import time
from psycopg2 import pool

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
OPENAI_API_KEY = "REDACTED_OPENAI_KEY"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# DB Pool
db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DB_CONNECTION_STRING)

sys_instruction = "You are an Expert Legal Analyst and Senior Bar Reviewer. Create 3-5 high-quality flashcards focusing on DOCTRINE, RULING, and KEY FACTS."

prompt_template = """
TASK: Create 3-5 high-quality flashcards for this Philippine Supreme Court case.
FORMAT: Return a JSON Array of objects. Each object must have "question" and "answer".

TEXT:
{text}

RETURN JSON ARRAY ONLY:
"""

def process_single_case(cid, text, client, model_name="gpt-5"):
    conn = None
    try:
        header_text = text[:15000] # OpenAI context is large
        prompt = prompt_template.format(text=header_text)
        
        if model_name.startswith("gpt-5") or model_name.startswith("o1"):
            # Reasoning Model Logic
            messages = [{"role": "user", "content": f"{sys_instruction}\n\n{prompt}"}]
            response = client.chat.completions.create(
                model=model_name,
                messages=messages
            )
        else:
            # Standard Logic
            messages = [
                {"role": "system", "content": sys_instruction},
                {"role": "user", "content": prompt}
            ]
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

        content = response.choices[0].message.content.strip()
        # Clean potential markdown fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        flashcards = json.loads(content)
        
        if isinstance(flashcards, dict) and "flashcards" in flashcards:
            flashcards = flashcards["flashcards"]

        if flashcards and isinstance(flashcards, list):
            conn = db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sc_decided_cases
                    SET flashcards = %s,
                        ai_model = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(flashcards), model_name, cid))
                conn.commit()
            logging.info(f"Updated {cid}: Generated {len(flashcards)} cards with {model_name}")
        
    except Exception as e:
        logging.error(f"Error {cid}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def backfill():
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    conn = db_pool.getconn()
    cur = conn.cursor()
    
    # Process only the 7 remaining or NULL flashcards
    cur.execute("""
        SELECT id, full_text_md 
        FROM sc_decided_cases 
        WHERE (flashcards IS NULL OR flashcards = '[]'::jsonb)
        AND full_text_md IS NOT NULL
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    db_pool.putconn(conn)
    
    print(f"Loaded {len(rows)} cases for OpenAI Flashcard generation.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for row in rows:
             cid, text = row
             futures.append(executor.submit(process_single_case, cid, text, client, "gpt-5"))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    backfill()
