import os
import json
import psycopg2
import google.generativeai as genai
import time
import logging
import sys
import argparse
from psycopg2.extras import RealDictCursor

# Configuration
API_KEY = os.environ.get("GOOGLE_API_KEY") or "REDACTED_API_KEY_HIDDEN"
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

# Model Configuration
# Model Configuration
# Model Configuration
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.0-flash' 
model = genai.GenerativeModel(MODEL_NAME)

SAFETY_SETTINGS = {
    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def fetch_and_claim_case(start_year, end_year, metadata_only=False):
    """
    Fetches a case that needs metadata/significance backfill.
    Claims it by setting digest_significance = 'PROCESSING'.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Query for backfill candidates
        
        target_conditions = """
                  short_title IS NULL OR short_title = '' OR
                  division IS NULL OR division = '' OR
                  ponente IS NULL OR ponente = ''
        """
        
        # New Logic: Only backfill significance if digest exists
        if not metadata_only:
            target_conditions += """
                  OR (
                      (digest_significance IS NULL OR digest_significance = '') 
                      AND 
                      (digest_facts IS NOT NULL AND digest_facts != '')
                  )
            """
            
        digest_processing_check = """
              AND (digest_significance NOT LIKE '%%PROCESSING%%' OR digest_significance IS NULL)
        """

        query = f"""
            SELECT id, full_text_md, case_number, digest_facts
            FROM sc_decided_cases
            WHERE date >= %s AND date <= %s
              AND full_text_md IS NOT NULL 
              AND full_text_md != ''
              {digest_processing_check}
              AND (
                  {target_conditions}
              )
            ORDER BY date DESC, id DESC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """
        
        # Start and end dates for the query
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        
        cur.execute(query, (start_date, end_date))
        case = cur.fetchone()
        
        if not case:
            conn.close()
            return None
            
        case_id = case[0]
        logging.info(f"Claiming Case ID {case_id} ({case[2]})...")
        
        # Mark as PROCESSING
        cur.execute("UPDATE sc_decided_cases SET digest_significance = 'PROCESSING' WHERE id = %s", (case_id,))
        conn.commit()
        
        return case
        
    except Exception as e:
        logging.error(f"Error fetching case: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

# ... (generate_metadata_significance and save_result omitted, unchanged) ...

def generate_metadata_significance(content, metadata_only=False):
    
    task_goal = "Analyze the provided legal text and extract proper Metadata and generate the 'Significance' section for Bar Review students."
    significance_rule = """
    4. **Significance (Bar Traps):**
         * **Step A: Primary Classification:** [REITERATION | NEW DOCTRINE | ABANDONMENT | MODIFICATION | REVERSAL OF DECISION]
         * **Step B: Reasoning:** Provide a `classification_reasoning` sentence. If New Doctrine/Abandonment/Modification, YOU MUST QUOTE the specific sentence where the Court indicates this.
         * **Step C: Collateral Matters:** Scan for "Bar Exam Traps": Quantum of Proof changes, Win/Loss paradoxes, Procedural anomalies, Prospective applications, Novel definitions. Merge this into `significance_narrative`.
    """
    output_schema = """
        "classification": "REITERATION | NEW DOCTRINE | ...",
        "classification_reasoning": "Evidence...",
        "significance_narrative": "Detailed explanation of Bar Traps and significance..."
    """
    
    if metadata_only:
        task_goal = "Analyze the provided legal text and extract proper Metadata ONLY (Short Title, Division, Ponente)."
        significance_rule = "" # No significance rule
        output_schema = "" # No significance schema

    prompt = f"""
    You are a Senior Legal Editor and Bar Review Lecturer for the Philippine Supreme Court.

    **INPUT TEXT:**
    {content[:30000]} 

    **YOUR GOAL:**
    {task_goal}

    **STRICT RULES:**
    1. **Short Title:** STRICTLY follow the **2023 Supreme Court Stylebook**:
         * **General Rule:** "Petitioner v. Respondent". Use **v.** (not "vs."). 
         * **Specific Rules:** Omit "The" at the start (e.g., "Coca-Cola Bottlers" NOT "The Coca-Cola..."). People cases: "People v. [Accused]". Use full compound surnames. Only use the first named party.
    2. **Court Body:** En Banc vs. Division.
    3. **Ponente:** Justice Name.
    {significance_rule}

    **OUTPUT FORMAT:**
    Return ONLY valid JSON:
    {{
        "short_title": "...",
        "court_division": "En Banc | Third Division",
        "ponente": "..."{"," if not metadata_only else ""}
        {output_schema}
    }}
    """
    
    try:
        response = model.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        logging.error(f"AI Generation Error: {e}")
        return None

def save_result(case_id, data):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        update_clauses = []
        params = []
        
        if data.get('short_title'):
             update_clauses.append("short_title = COALESCE(NULLIF(short_title, ''), %s)")
             params.append(data['short_title'])
             
        if data.get('court_division'):
             update_clauses.append("division = COALESCE(NULLIF(division, ''), %s)") 
             params.append(data['court_division'])

        if data.get('ponente'):
             update_clauses.append("ponente = COALESCE(NULLIF(ponente, ''), %s)")
             params.append(data['ponente'])

        if data.get('classification'):
             update_clauses.append("significance_category = COALESCE(NULLIF(significance_category, ''), %s)")
             params.append(data['classification'])
             
        if data.get('significance_narrative'):
             update_clauses.append("digest_significance = COALESCE(NULLIF(digest_significance, 'PROCESSING'), %s)")
             params.append(data['significance_narrative'])
        else:
             pass

        # Always update updated_at and model
        update_clauses.append("updated_at = NOW()")
        update_clauses.append(f"ai_model = COALESCE(ai_model, '{MODEL_NAME}')") 

        if not update_clauses:
            logging.warning(f"No data to save for {case_id}")
            # Reset processing status
            cur.execute("UPDATE sc_decided_cases SET digest_significance = NULL WHERE id = %s AND digest_significance = 'PROCESSING'", (case_id,))
            conn.commit()
            return

        query = f"UPDATE sc_decided_cases SET {', '.join(update_clauses)} WHERE id = %s"
        params.append(case_id)
        
        cur.execute(query, tuple(params))
        conn.commit()
        logging.info(f"Saved Case {case_id}")
        
    except Exception as e:
        logging.error(f"Error saving: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--start-year", type=int, default=1901)
    parser.add_argument("--end-year", type=int, default=1989)
    parser.add_argument("--metadata-only", action="store_true", help="Only backfill metadata, skip significance")
    args = parser.parse_args()
    
    logging.info(f"Starting worker for range {args.start_year}-{args.end_year} (Metadata Only: {args.metadata_only})")
    
    while True:
        case = fetch_and_claim_case(args.start_year, args.end_year, metadata_only=args.metadata_only)
        if not case:
            logging.info("No more cases to process.")
            break
            
        try:
            case_id, content, _, digest_facts = case # Unpack 4 values now
            
            # Determine logic: 
            # If metadata_only arg is True, we enforce it.
            # If digest_facts is None, we also enforce metadata_only mode for THIS case.
            effective_metadata_only = args.metadata_only or (not digest_facts)
            
            data = generate_metadata_significance(content, metadata_only=effective_metadata_only)
            
            if data:
                save_result(case_id, data)
            else:
                logging.error(f"Failed to generate JSON for {case_id}")
                # Reset processing tag
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE sc_decided_cases SET digest_significance = NULL WHERE id = %s", (case_id,))
                conn.commit()
                conn.close()
                
            time.sleep(0.5) # Rate limit protection
            
        except Exception as e:
            logging.error(f"Loop Error: {e}")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE sc_decided_cases SET digest_significance = NULL WHERE id = %s", (case_id,))
                conn.commit()
                conn.close()
            except:
                pass

if __name__ == "__main__":
    main()
