import psycopg2
import json
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        with open('src/backend/local.settings.json') as f:
            settings = json.load(f)
            return settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        return "postgresql://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"

def get_missing(year):
    conn_str = get_conn_str()
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print(f"--- Missing ROC Links for {year} ---")
    cur.execute("""
        SELECT id, short_title
        FROM sc_decided_cases
        WHERE (statutes_involved::text ILIKE '%%Rules of Court%%' OR statutes_involved::text ILIKE '%%ROC%%')
          AND EXTRACT(YEAR FROM date) = %s
          AND id NOT IN (SELECT DISTINCT case_id FROM codal_case_links WHERE statute_id = 'ROC')
        ORDER BY id DESC
    """, (year,))
    
    rows = cur.fetchall()
    for r in rows:
        print(f"ID: {r['id']} | {r['short_title']}")
    
    print(f"Total Missing: {len(rows)}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    get_missing(2025)
    print("\n")
    get_missing(2024)
