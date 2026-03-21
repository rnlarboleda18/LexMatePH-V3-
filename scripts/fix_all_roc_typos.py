import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
import json
import time
import sys

DB_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
API_KEY = "REDACTED_API_KEY_HIDDEN"

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-2.0-flash"

def main():
    commit = "--commit" in sys.argv
    print(f"Connecting to Cloud DB... Mode: {'COMMIT' if commit else 'DRY RUN'}")
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur_write = conn.cursor()

    print("Fetching all unique ROC titles from Cloud DB...")
    cur.execute("SELECT DISTINCT article_title FROM roc_codal WHERE article_title IS NOT NULL")
    rows = cur.fetchall()
    
    if not rows:
         print("No titles found.")
         return

    titles = [r['article_title'].strip() for r in rows if r['article_title'].strip()]
    print(f"Loaded {len(titles)} unique titles.")

    # We feed the titles list to Gemini in batches or one large prompt 
    # to find words that have accidental spaces inside them.
    # We ask for a JSON map { "original": "fixed" } only for ones that NEED fixing.

    prompt = f"""
You are a Philippine Legal Editor. Review the list of section titles below.
They were parsed from a PDF and have accidental SPACES INSIDE WORDS due to OCR errors (e.g., "defi ned" -> "defined", "off er" -> "offer", "qualifi cations" -> "qualifications").

TASK:
Identify which titles contain spaced typos, and return a fixed map.
*   Only include titles that had an actual typo.
*   Preserve legitimate spaces between words (e.g. "Necessary party" is correct and has a space).
*   Correct terms like: "defi ned", "off er", "qualifi cations", "sub ject", "confi ned".

LIST:
{json.dumps(titles, indent=2)}

OUTPUT ONLY VALID JSON:
{{
  "original_title": "fixed_title"
}}
"""

    try:
        print("Calling Gemini to identify typos...")
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        try:
             fix_map = json.loads(response.text)
        except:
             clean_text = response.text.replace("```json", "").replace("```", "").strip()
             fix_map = json.loads(clean_text)

        # Handle Gemini returning a list of dicts instead of a flat dict
        if isinstance(fix_map, list):
             new_map = {}
             for item in fix_map:
                  if isinstance(item, dict):
                       new_map.update(item)
             fix_map = new_map

        print(f"\nGemini found {len(fix_map)} titles requiring repair:\n")
        
        fixed_count = 0
        for orig, fixed in fix_map.items():
            # Verify the original actually exists (Gemini might slight rewrite)
            if orig in titles and orig != fixed:
                 fixed_count += 1
                 print(f"  [Fix] {orig!r} -> {fixed!r}")
                 if commit:
                      cur_write.execute("UPDATE roc_codal SET article_title = %s, updated_at = NOW() WHERE article_title = %s", (fixed, orig))

        print("\n" + "=" * 50)
        if commit:
             conn.commit()
             print(f"🎉 Successfully repaired {fixed_count} title typos in Cloud!")
        else:
             print(f"🔍 Dry-run found {fixed_count} fixes to apply on Cloud. Run with `--commit` to execute.")

    except Exception as e:
        print(f"Error during repair iteration: {e}")

    cur.close()
    cur_write.close()
    conn.close()

if __name__ == "__main__":
    main()
