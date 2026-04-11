import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def load_settings():
    try:
        with open("local.settings.json") as f:
            data = json.load(f)
            vals = data.get("Values", {})
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

load_settings()

conn_str = os.environ.get("DB_CONNECTION_STRING") or ""
if ":5432/" in conn_str:
    conn_str = conn_str.replace(":5432/", ":5432/")

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Fetch 1 question matching PIL
    cur.execute("""
        SELECT id, year, subject, sub_topic, text 
        FROM questions 
        WHERE sub_topic = 'Public International Law' 
        ORDER BY RANDOM() LIMIT 1
    """)
    row = cur.fetchone()
    if row:
        print(json.dumps(row, indent=2))
    else:
        print("No PIL questions found.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
