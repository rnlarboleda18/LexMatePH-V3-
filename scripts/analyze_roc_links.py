import psycopg2
import json
import os
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        with open('src/backend/local.settings.json') as f:
            settings = json.load(f)
            return settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        # Fallback to standard prod connection if local settings fail/missing in this path
        return "postgresql://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"

def analyze():
    conn_str = get_conn_str()
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("--- ROC Linking Analysis ---")
    
    # 1. Total ROC provisions in codal
    cur.execute("SELECT count(*) FROM roc_codal")
    total_provisions = cur.fetchone()['count']
    print(f"Total ROC Provisions in Codal: {total_provisions}")

    # 2. Total Links for ROC
    cur.execute("SELECT count(*) FROM codal_case_links WHERE statute_id = 'ROC'")
    total_links = cur.fetchone()['count']
    print(f"Total Case Links for ROC: {total_links}")

    # 3. Breakdown per year (Potential vs Actual)
    print("\nYearly Coverage (Cases tagged with ROC vs Linked):")
    cur.execute("""
        WITH potential AS (
            SELECT EXTRACT(YEAR FROM date) as year, count(*) as count
            FROM sc_decided_cases
            WHERE (statutes_involved::text ILIKE '%%Rules of Court%%' OR statutes_involved::text ILIKE '%%ROC%%')
            GROUP BY 1
        ),
        linked AS (
            SELECT EXTRACT(YEAR FROM s.date) as year, count(DISTINCT l.case_id) as count
            FROM codal_case_links l
            JOIN sc_decided_cases s ON l.case_id = s.id
            WHERE l.statute_id = 'ROC'
            GROUP BY 1
        )
        SELECT 
            COALESCE(p.year, l.year) as year,
            COALESCE(p.count, 0) as potential_count,
            COALESCE(l.count, 0) as linked_count,
            CASE WHEN p.count > 0 THEN ROUND((COALESCE(l.count, 0)::numeric / p.count) * 100, 2) ELSE 0 END as pct
        FROM potential p
        FULL OUTER JOIN linked l ON p.year = l.year
        WHERE COALESCE(p.year, l.year) >= 2018
        ORDER BY year DESC
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"Year {int(r['year'])}: {r['linked_count']}/{r['potential_count']} cases linked ({r['pct']}%)")

    cur.close()
    conn.close()

if __name__ == "__main__":
    analyze()
