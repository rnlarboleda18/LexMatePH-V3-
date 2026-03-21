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
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'roc_codal'")
print("Columns in roc_codal:")
print([r[0] for r in cur.fetchall()])
conn.close()
