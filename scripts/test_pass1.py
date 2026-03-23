import google.generativeai as genai
import time
import json
import psycopg2

API_KEY = "REDACTED_API_KEY_HIDDEN"
genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-2.0-flash"

PASS1_SCHEMA = """
{
  "hits": [
    {"rule": "110", "section": "1"}
  ]
}
"""

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor()
        cur.execute("SELECT short_title, main_doctrine, digest_ratio, digest_ruling FROM sc_decided_cases WHERE (statutes_involved::text ILIKE '%%Rules of Court%%' OR statutes_involved::text ILIKE '%%ROC%%') OFFSET 3 LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            print("No case found.")
            return

        case = {
            'short_title': row[0],
            'main_doctrine': row[1],
            'digest_ratio': row[2],
            'digest_ruling': row[3]
        }

        prompt = f"""
You are a Philippine legal expert. Analyse the Supreme Court case digest below 
and list every specific Rules of Court (ROC) provision it INTERPRETS or APPLIES.

CASE:
Title: {case.get('short_title', '')}
Doctrine: {case.get('main_doctrine') or 'N/A'}
Ratio: {case.get('digest_ratio') or 'N/A'}
Ruling: {case.get('digest_ruling') or 'N/A'}

TASK:
Return a JSON list of provision hits containing "rule" and "section" strings.
Example: Rule 110, Section 1 -> {{"rule": "110", "section": "1"}}

OUTPUT ONLY JSON:
{PASS1_SCHEMA}
"""
        print("Calling Gemini...")
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        print("Response received:")
        print(response.text)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
