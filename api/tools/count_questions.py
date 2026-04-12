import os
import json
import psycopg2

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
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM questions")
    count = cur.fetchone()[0]
    print(f"EXACT_COUNT={count}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
