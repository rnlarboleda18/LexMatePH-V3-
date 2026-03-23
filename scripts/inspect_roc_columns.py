import psycopg2
import json

def get_db_connection():
    try:
        with open('api/local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

conn = get_db_connection()
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'roc_codal'")
columns = cur.fetchall()

print("Columns in roc_codal:")
for c in columns:
    print(c[0])

cur.close()
conn.close()
