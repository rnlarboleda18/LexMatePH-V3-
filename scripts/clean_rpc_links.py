import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

cur.execute("DELETE FROM codal_case_links WHERE statute_id = 'RPC'")
deleted = cur.rowcount
conn.commit()

print(f"✅ Deleted {deleted} RPC links from database")

conn.close()
