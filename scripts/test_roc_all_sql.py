import psycopg2
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
except Exception:
    conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

conn = psycopg2.connect(conn_str)
cur = conn.cursor()

try:
    print("Testing SQL Query for /api/roc/all...")
    cur.execute("""
        SELECT * FROM roc_codal 
        ORDER BY 
            book ASC,
            CAST(REGEXP_REPLACE(title_label, '\D', '', 'g') AS INTEGER) ASC,
            section_num ASC
    """)
    rows = cur.fetchall()
    print(f"Success! Fetched {len(rows)} rows.")
except Exception as e:
    print(f"SQL Error: {e}")

cur.close()
conn.close()
