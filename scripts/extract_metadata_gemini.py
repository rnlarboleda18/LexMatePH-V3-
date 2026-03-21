import os
import json
import psycopg2
from google import genai
from google.genai import types
import time
import logging
import argparse

# Configuration
API_KEY = os.environ.get("GOOGLE_API_KEY") or "REDACTED_API_KEY_HIDDEN"
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

# Client Configuration
client = genai.Client(api_key=API_KEY)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    return conn

def fetch_case(conn, force=False, target_ids=None, limit=1):
    cur = conn.cursor()
    try:
        query = """
            SELECT id, full_text_md, case_number 
            FROM sc_decided_cases 
            WHERE full_text_md IS NOT NULL 
              AND full_text_md != '' 
        """
        params = []

        if target_ids:
            safe_ids = [int(x) for x in target_ids if x.isdigit()]
            if safe_ids:
                placeholders = ','.join(['%s'] * len(safe_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(safe_ids)
            else:
                return None
        elif not force:
            # Target cases where ANY of the target fields are missing
            query += """
                AND (
                    case_number IS NULL OR case_number = '' OR
                    short_title IS NULL OR short_title = '' OR
                    document_type IS NULL OR document_type = '' OR
                    division IS NULL OR division = '' OR
                    ponente IS NULL OR ponente = ''
                )
            """
        
        # Order by ID to have deterministic processing or by updated_at? 
        # Random/Sequential is fine. Let's do ID ASC to go through them systematically.
        query += " ORDER BY id ASC LIMIT %s FOR UPDATE SKIP LOCKED"
        params.append(limit)

        cur.execute(query, tuple(params))
        cases = cur.fetchall()
        return cases

    except Exception as e:
        logging.error(f"Error fetching case: {e}")
        return []

    # Dynamic truncation to satisfy "only up to the ponente"
    # Strategy: Find "Ponente" keyword or "J.:" (Justice signature) and cut shortly after.
    # Fallback: First 5000 characters (usually covers header).
    lower_content = content[:10000].lower() # Search primarily in the first 10k
    
    cutoff_index = -1
    
    # 1. Look for explicit "Ponente" label
    p_index = lower_content.find("ponente")
    if p_index != -1:
        cutoff_index = p_index + 300 # Capture the label + ample space for the name
    
    # 2. Look for "J.:" or "J:" (common pattern "LEONEN, J.:")
    if cutoff_index == -1:
        j_index = lower_content.find("j.:")
        if j_index != -1:
             cutoff_index = j_index + 100
    
    if cutoff_index == -1:
        # Fallback
        trunc_content = content[:5000]
    else:
        trunc_content = content[:cutoff_index]

    prompt = f"""
    **ROLE:**
    You are a precise Legal Data Extractor. Your ONLY job is to extract 5 specific metadata fields from the provided Philippine Supreme Court decision.

    **INPUT TEXT:**
    {trunc_content} 

    **TASK:**
    Extract the following fields. Return NULL if not found.

    1. **case_number**: The G.R. No. or A.M. No. (e.g., "G.R. No. 123456").
    
    2. **short_title**: STRICTLY follow the **2023 Supreme Court Stylebook** for "Short Title" construction. This is the abbreviated name used in subsequent references (e.g., "As held in [Short Title]...").
       - **General Rule:** Use the surname of the first party (e.g., "Leonen").
       - **Criminal Cases:** Use "**People v. [Accused]**" (e.g., "People v. Estrada").
       - **Corporations:** Use full name or acronym (e.g., "Meralco").
       
    3. **document_type**: "Decision" or "Resolution".
    4. **division**: The court division (e.g., "En Banc", "First Division").
    5. **ponente**: The Justice who authored the decision.

    **OUTPUT FORMAT:**
    Return ONLY valid JSON:
    {{
        "case_number": "...",
        "short_title": "...",
        "document_type": "...",
        "division": "...",
        "ponente": "..."
    }}
    """

    model_name = "gemini-2.5-flash-lite"
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.0
            )
        )
        
        if not response.text:
            logging.warning(f"Empty response for Case {case_id}")
            return None

        return json.loads(response.text)

    except Exception as e:
        logging.error(f"AI Error for Case {case_id}: {e}")
        return None

def update_db(conn, case_id, data):
    cur = conn.cursor()
    try:
        # We only update if the new value is NOT NULL (to avoid wiping existing data if AI fails to find it but it exists? 
        # Actually, if AI returns null, maybe we should leave it. 
        # COALESCE matches the safe update strategy.)
        cur.execute("""
            UPDATE sc_decided_cases 
            SET 
                case_number = COALESCE(case_number, %s),
                short_title = COALESCE(short_title, %s),
                document_type = COALESCE(document_type, %s),
                division = COALESCE(division, %s),
                ponente = COALESCE(ponente, %s),
                updated_at = NOW()
            WHERE id = %s
        """, (
            data.get('case_number'),
            data.get('short_title'),
            data.get('document_type'),
            data.get('division'),
            data.get('ponente'),
            case_id
        ))
        conn.commit()
        logging.info(f"Updated Metadata for Case {case_id}: {data}")
    except Exception as e:
        logging.error(f"DB Error for Case {case_id}: {e}")
        conn.rollback()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--force", action="store_true", help="Process even if fields are already filled")
    parser.add_argument("--continuous", action="store_true", help="Run continuously until no cases are found")
    parser.add_argument("--target-ids", type=str, help="Comma-separated list of IDs")
    args = parser.parse_args()

    target_ids_list = None
    if args.target_ids:
        target_ids_list = [x.strip() for x in args.target_ids.split(',') if x.strip().isdigit()]

    conn = get_db_connection()
    
    while True:
        try:
            # We fetch in a loop or batch? The prompt logic is per-case.
            # Let's fetch 'limit' cases.
            cases = fetch_case(conn, force=args.force, target_ids=target_ids_list, limit=args.limit)
            
            if not cases:
                logging.info("No cases found to process.")
                if args.continuous:
                    logging.info("Waiting 60s before retry...")
                    time.sleep(60)
                    continue
                else:
                    break

            logging.info(f"Found {len(cases)} cases to process.")

            for case in cases:
                case_id = case[0]
                content = case[1]
                
                logging.info(f"Processing Case {case_id}...")
                data = extract_metadata(case_id, content)
                
                if data:
                    update_db(conn, case_id, data)
                    time.sleep(1) # Rate limit politeness
                else:
                    logging.warning(f"Failed to extract/parse data for Case {case_id}")
            
            if not args.continuous:
                break
                
        except Exception as e:
            logging.error(f"Loop Error: {e}")
            if args.continuous:
                time.sleep(10)
            else:
                break

    conn.close()

if __name__ == "__main__":
    main()
