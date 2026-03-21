import os
import json
import psycopg2
import google.generativeai as genai
import logging
import concurrent.futures

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
API_KEY = os.environ.get("GOOGLE_API_KEY", "REDACTED_API_KEY_HIDDEN")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

prompt_template = """
TASK: Extract a CONCISE Short Title for this case following the 2023 Supreme Court Stylebook.
RULES:
1. **NO 'et al.'**: Never use "et al.", "and others", or similar. Omit subsequent parties entirely.
2. **First Party Only**: Use only the first petitioner vs. the first respondent.
3. **Surnames Only**: Use surnames for individuals (e.g., "Cruz v. Santos"). Do not use first names.
4. **Agencies**: Omit titles like "The Honorable", "Commissioner of", "People of the Philippines".
   - Exception: For Criminal cases, use "**People of the Philippines v. [Accused]**" (or just "People v. [Accused]").
   - Government agencies: Use the agency name (e.g., "Social Security System", "Commission on Elections").
5. **Length**: Keep it extremely concise (under 100 chars preferred).

FORMAT: "[First Petitioner] v. [First Respondent]"

TEXT:
{text}

RETURN JSON:
{{
    "short_title": "..."
}}
"""

def process_single_case(cid, text, model):
    try:
        logging.info(f"Processing {cid}...")
        header_text = text[:5000] # Header is enough for title
        
        response = model.generate_content(prompt_template.format(text=header_text), generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        new_title = data.get('short_title')
        
        if new_title:
            with get_db_connection() as thread_conn:
                with thread_conn.cursor() as thread_cur:
                    # OVERWRITE logic
                    thread_cur.execute("""
                        UPDATE sc_decided_cases
                        SET short_title = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (new_title, cid))
                    thread_conn.commit()
            logging.info(f"Updated {cid}: {new_title}")
        
    except Exception as e:
        logging.error(f"Error {cid}: {e}")

def fix_titles():
    genai.configure(api_key=API_KEY)
    # User requested gemini 2.0 flash (no exp)
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
    except:
        logging.warning("gemini-2.0-flash not found, falling back to gemini-1.5-flash")
        model = genai.GenerativeModel("gemini-1.5-flash")
    
    # 1. Load Original Long Titles (User request "all these cases")
    target_ids = set()
    try:
        with open("long_titles_ids.txt", "r") as f:
            file_ids = f.read().strip().split(',')
            target_ids.update([int(x) for x in file_ids if x])
    except:
        pass

    # 2. Fetch ANY case with "et al." (Cleanup Policy)
    conn = get_db_connection()
    cur = conn.cursor()
    print("Fetching 'et al.' cases from DB...")
    cur.execute("SELECT id FROM sc_decided_cases WHERE short_title LIKE '%et al.%'")
    et_al_rows = cur.fetchall()
    et_al_ids = [r[0] for r in et_al_rows]
    target_ids.update(et_al_ids)
    
    final_ids = list(target_ids)
    print(f"Loaded {len(final_ids)} unique cases to fix ({len(et_al_ids)} had 'et al.').")

    # Fetch Data
    cur.execute(f"SELECT id, full_text_md FROM sc_decided_cases WHERE id = ANY(%s)", (final_ids,))
    rows = cur.fetchall()
    conn.close()

    # Threaded Processing
    print(f"Fixing {len(rows)} titles with 2 workers (Gemini 2.0 Flash)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for row in rows:
             cid, text = row
             futures.append(executor.submit(process_single_case, cid, text, model))
             
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    fix_titles()
