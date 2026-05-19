import os
import json
import psycopg2

def load_env():
    try:
        with open('api/local.settings.json', encoding="utf-8") as f:
            vals = json.load(f).get("Values") or {}
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[str(k)] = str(v)
    except Exception as e:
        print("Error loading env:", e)

load_env()
db_str = os.environ.get("DB_CONNECTION_STRING")
print("Connecting to:", db_str.split('@')[-1] if '@' in db_str else db_str)

try:
    conn = psycopg2.connect(db_str)
    cur = conn.cursor()
    statutes = ('AM-07-9-12-SC', 'AM-08-1-16-SC', 'AM-09-6-8-SC', 'AM-01-7-01-SC', 'CPRA', 'AM-02-8-13-SC', 'NCJC', 'RA-11642')
    cur.execute("SELECT statute_id, COUNT(*) FROM codal_case_links WHERE statute_id IN %s GROUP BY statute_id", (statutes,))
    rows = cur.fetchall()
    print("Links found:")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
    if not rows:
        print("  0 links")
except Exception as e:
    print("DB error:", e)
