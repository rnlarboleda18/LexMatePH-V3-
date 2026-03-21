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
cur.execute("SELECT * FROM roc_codal LIMIT 1")
colnames = [desc[0] for desc in cur.description]
print(f"Columns: {colnames}")
row = cur.fetchone()
if row:
    print(f"Row values: {dict(zip(colnames, row))}")
else:
    print("No rows found in roc_codal.")
conn.close()
