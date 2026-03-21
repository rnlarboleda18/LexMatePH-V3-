import psycopg2
from psycopg2.extras import RealDictCursor
import json

DB_CONNECTION = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT pid, query, state, wait_event_type, wait_event FROM pg_stat_activity WHERE datname = 'bar_reviewer_local' AND state != 'idle';")
    rows = cur.fetchall()
    print(json.dumps(rows, indent=2, default=str))
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
