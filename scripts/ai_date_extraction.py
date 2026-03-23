import os
import psycopg2
from google import genai
from google.genai import types
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
API_KEY = os.environ.get("GOOGLE_API_KEY") or "REDACTED_API_KEY_HIDDEN"

client = genai.Client(api_key=API_KEY)

def process_case(case_data):
    case_id, text = case_data
    # Truncate text to header/footer areas where dates usually live
    excerpt = text[:3000] + "\n...[middle omitted]...\n" + text[-1000:]
    
    prompt = f"""
    Task: Extract the Promulgation Date (Date of Decision) from the Philippine Supreme Court decision below.
    
    Instructions:
    1. Look for lines like "Promulgated:", "Promulgated on", "Manila, [Date]", or the date at the top/bottom.
    2. Return ONLY the date in YYYY-MM-DD format (ISO 8601).
    3. If NO date is found, return "NULL".
    
    Text:
    {excerpt}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE"
                    ),
                ]
            )
        )
        
        result = response.text.strip()
        
        if re.match(r'^\d{4}-\d{2}-\d{2}$', result):
            print(f"Case {case_id}: Found {result}", flush=True)
            return (result, case_id)
        elif result == "NULL":
            print(f"Case {case_id}: AI found no date.", flush=True)
            return None
        else:
            print(f"Case {case_id}: Invalid format '{result}'", flush=True)
            return None
            
    except Exception as e:
        print(f"Error processing Case {case_id}: {e}", flush=True)
        return None

def extract_dates_ai():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    try:
        print("Fetching cases with NULL date (excluding REDIGEST)...", flush=True)
        cur.execute("""
            SELECT id, full_text_md 
            FROM sc_decided_cases 
            WHERE date IS NULL 
            AND case_number != 'REDIGEST'
            AND full_text_md IS NOT NULL 
            AND full_text_md != ''
            ORDER BY id ASC
        """)
        cases = cur.fetchall()
        print(f"Found {len(cases)} cases to process. Starting 10 workers...", flush=True)
        
        updates = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_case = {executor.submit(process_case, case): case for case in cases}
            
            for future in as_completed(future_to_case):
                res = future.result()
                if res:
                    updates.append(res)
            
        # Update DB
        if updates:
            print(f"\nUpdating {len(updates)} cases...", flush=True)
            cur.executemany("""
                UPDATE sc_decided_cases 
                SET date = %s, updated_at = NOW() 
                WHERE id = %s
            """, updates)
            conn.commit()
            print("Updates committed.", flush=True)
        else:
            print("No updates found.", flush=True)

    except Exception as e:
        print(f"DB Error: {e}", flush=True)
    finally:
        conn.close()

if __name__ == "__main__":
    extract_dates_ai()
