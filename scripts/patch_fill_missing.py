import os
import psycopg2
import google.generativeai as genai
import json
import time
import traceback

# Config
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 
MODEL_NAME = "gemini-2.5-flash-lite"

# Target ID: 53750 (G.R. No. E-02219)
TARGET_IDS = [53750]

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

METADATA_PROMPT = """
You are a legal expert being asked to extract metadata from a Philippine Supreme Court decision.
DO NOT generate a digest (facts, issues, ruling). ONLY extract the identifying information.

Output strictly JSON with the following keys:
{
  "short_title": "Standard format (e.g., People v. X) - Remove * or _",
  "full_title": "The complete caption of the case",
  "court_division": "En Banc or Division",
  "ponente": "Justice who authored the decision (Format: 'X, J.')",
  "decision_date": "YYYY-MM-DD",
  "main_doctrine": "The core legal principle established (1-2 sentences)",
  "subject": "Format exactly as: 'Primary: [Main Topic]; Secondary: [Sub-topic 1], [Sub-topic 2]'",
  "timeline": [{"year": "YYYY", "event": "Brief description"}] (extract if relevant dates exist)
}

If a field cannot be found, use null.
"""

# Kept for fallback, though likely unused for this case if facts exist
FULL_PROMPT = """
You are a top-tier Philippine Bar Reviewer and Legal expert.
Create a comprehensive case digest and extract metadata for this Supreme Court decision.

Output strictly JSON with the following keys:
{
  "short_title": "Standard format (e.g., People v. X) - Remove * or _",
  "full_title": "Complete caption",
  "court_division": "En Banc or Division",
  "ponente": "Justice Author",
  "decision_date": "YYYY-MM-DD",
  "main_doctrine": "The core legal principle (concise)",
  "digest_facts": "Markdown formatted facts (paragraphs)",
  "digest_issues": "Markdown formatted issues",
  "digest_ruling": "Markdown formatted ruling",
  "digest_significance": "Why this case matters for the Bar",
  "timeline": [{"year": "YYYY", "event": "Brief event"}],
  "legal_concepts": ["concept1", "concept2"],
  "subject": "Format exactly as: 'Primary: [Main Topic]; Secondary: [Sub-topic 1], [Sub-topic 2]'"
}
"""

def clean_json_text(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def process_case(cur, case_id):
    # Fetch case content
    cur.execute("SELECT case_number, full_text_md, digest_facts FROM sc_decided_cases WHERE id = %s", (case_id,))
    row = cur.fetchone()
    
    if not row:
        print(f"ID {case_id} not found.")
        return

    case_number, original_text, current_facts = row
    print(f"Processing {case_number} (ID: {case_id})...")

    if not original_text:
        print(f"  SKIPPING: No original_text found for {case_number}.")
        return

    # Determine Strategy
    has_facts = bool(current_facts) and len(current_facts) > 50
    
    if has_facts:
        print("  -> Has Facts. Running METADATA Patch only.")
        prompt_text = METADATA_PROMPT + "\n\nCASE TEXT:\n" + original_text[:50000] # Limit context if needed
        mode = "metadata"
    else:
        print("  -> Missing Facts. Running FULL Digestion.")
        prompt_text = FULL_PROMPT + "\n\nCASE TEXT:\n" + original_text[:50000]
        mode = "full"

    # Call AI
    try:
        response = model.generate_content(prompt_text)
        result_json = json.loads(clean_json_text(response.text))
    except Exception as e:
        print(f"  ERROR: AI generation failed: {e}")
        return

    short_title = result_json.get('short_title')
    if short_title:
        short_title = short_title.strip().strip('*').strip('_').strip()

    # Update DB
    if mode == "metadata":
        update_query = """
            UPDATE sc_decided_cases 
            SET 
                short_title = %s,
                title = %s,
                division = %s,
                ponente = %s,
                main_doctrine = %s,
                subject = %s,
                timeline = %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
        """
        cur.execute(update_query, (
            short_title,
            result_json.get('full_title'),
            result_json.get('court_division'),
            result_json.get('ponente'),
            result_json.get('main_doctrine'),
            result_json.get('subject'),
            json.dumps(result_json.get('timeline', [])),
            case_id
        ))
        print(f"  -> Updated Metadata (Title: {short_title})")

    else: # Full Mode
        update_query = """
            UPDATE sc_decided_cases 
            SET 
                short_title = %s,
                title = %s,
                division = %s,
                ponente = %s,
                main_doctrine = %s,
                digest_facts = %s,
                digest_issues = %s,
                digest_ruling = %s,
                digest_significance = %s,
                timeline = %s::jsonb,
                legal_concepts = %s::jsonb,
                subject = %s,
                ai_model = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        cur.execute(update_query, (
            short_title,
            result_json.get('full_title'),
            result_json.get('court_division'),
            result_json.get('ponente'),
            result_json.get('main_doctrine'),
            result_json.get('digest_facts'),
            result_json.get('digest_issues'),
            result_json.get('digest_ruling'),
            result_json.get('digest_significance'),
            json.dumps(result_json.get('timeline', [])),
            json.dumps(result_json.get('legal_concepts', [])),
            result_json.get('subject'),
            MODEL_NAME, 
            case_id
        ))
        print(f"  -> Generated FULL Digest (Title: {short_title})")

def main():
    print("STARTING PATCH SCRIPT...", flush=True)
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()

        for cid in TARGET_IDS:
            print(f"Processing loop ID: {cid}", flush=True)
            try:
                process_case(cur, cid)
            except Exception as e:
                print(f"CRASH processing {cid}: {e}", flush=True)
                traceback.print_exc()
            time.sleep(2) 

        conn.close()
        print("Done.", flush=True)
    except Exception as outer_e:
        print(f"CRASH in main: {outer_e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
