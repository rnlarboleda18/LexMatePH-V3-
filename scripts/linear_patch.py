import os
import psycopg2
import google.generativeai as genai
import json

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 
MODEL_NAME = "gemini-2.5-flash-lite"

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

METADATA_PROMPT = """
You are a legal expert being asked to extract metadata from a Philippine Supreme Court decision.
Output strictly JSON with the following keys:
{
  "short_title": "Standard format (e.g., People v. X) - Remove * or _",
  "full_title": "The complete caption of the case",
  "court_division": "En Banc or Division",
  "ponente": "Justice who authored the decision (Format: 'X, J.')",
  "decision_date": "YYYY-MM-DD",
  "main_doctrine": "The core legal principle established",
  "subject": "Format exactly as: 'Primary: [Main Topic]; Secondary: [Sub-topic 1], [Sub-topic 2]'"
}
"""

print("Connecting...", flush=True)
conn = psycopg2.connect(DB_CONNECTION_STRING)
conn.autocommit = True
cur = conn.cursor()

cid = 53750
print(f"Fetching {cid}...", flush=True)
cur.execute("SELECT full_text_md FROM sc_decided_cases WHERE id = %s", (cid,))
row = cur.fetchone()

if not row:
    print("Row not found!")
    exit(1)

text = row[0]
print(f"Text length: {len(text)}", flush=True)

print("Generating...", flush=True)
prompt = METADATA_PROMPT + "\n\nCASE TEXT:\n" + text[:40000]
resp = model.generate_content(prompt)
print("Generated!", flush=True)

try:
    clean_text = resp.text.replace("```json", "").replace("```", "").strip()
    data = json.loads(clean_text)
    print("Parsed JSON:", data, flush=True)
except Exception as e:
    print("JSON Parse Error:", e)
    print("Raw Text:", resp.text)
    exit(1)

print("Updating DB...", flush=True)
cur.execute("""
    UPDATE sc_decided_cases 
    SET 
        short_title = %s,
        title = %s,
        division = %s,
        ponente = %s,
        main_doctrine = %s,
        subject = %s
    WHERE id = %s
""", (
    data.get('short_title'),
    data.get('full_title'),
    data.get('court_division'),
    data.get('ponente'),
    data.get('main_doctrine'),
    data.get('subject'),
    cid
))
print("Update Complete.", flush=True)
conn.close()
