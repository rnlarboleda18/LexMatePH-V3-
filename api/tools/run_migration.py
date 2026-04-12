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
# Force 5432 for local direct connection
if ":5432/" in conn_str:
    conn_str = conn_str.replace(":5432/", ":5432/")

sql = """
ALTER TABLE questions 
ADD COLUMN IF NOT EXISTS sub_topic VARCHAR(100) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_questions_sub_topic 
ON questions(sub_topic);

CREATE INDEX IF NOT EXISTS idx_questions_sub_topic_year 
ON questions(sub_topic, year DESC);
"""

try:
    print("Connecting to DB on port 5432...")
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()
    print("Running migration SQL...")
    cur.execute(sql)
    print("Migration SQL executed successfully.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Migration failed: {e}")
    exit(1)
