import os
import psycopg2

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

try:
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    print("--- DEEP DIAGNOSTIC 1901-1989 ---")
    
    # 1. Total
    cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1989")
    total = cur.fetchone()[0]
    print(f"Total Cases: {total}")

    # 2. "Done" by strict definition (Non-Null AND Non-Empty facts/ruling/significance)
    cur.execute("""
        SELECT COUNT(*) FROM sc_decided_cases 
        WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1989
        AND digest_facts IS NOT NULL AND digest_facts != ''
        AND digest_ruling IS NOT NULL AND digest_ruling != ''
        AND digest_significance IS NOT NULL AND digest_significance != ''
    """)
    done_strict = cur.fetchone()[0]
    print(f"Strictly Completed: {done_strict} ({done_strict/total*100:.2f}%)" if total else "0%")

    # 3. Junk Detector
    # Check for cases that are "Done" but have suspicious content (e.g. length < 20 chars)
    cur.execute("""
        SELECT COUNT(*) FROM sc_decided_cases 
        WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1989
        AND digest_facts IS NOT NULL 
        AND LENGTH(digest_facts) < 50
    """)
    suspicious_short = cur.fetchone()[0]
    print(f"Suspiciously Short Facts (<50 chars): {suspicious_short}")

    # 4. Stuck processing?
    cur.execute("""
        SELECT COUNT(*) FROM sc_decided_cases 
        WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1989
        AND digest_significance ILIKE '%PROCESSING%'
    """)
    processing = cur.fetchone()[0]
    print(f"Stuck Processing: {processing}")
    
    # 5. Blocked Safety?
    cur.execute("""
        SELECT COUNT(*) FROM sc_decided_cases 
        WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1989
        AND digest_significance = 'BLOCKED_SAFETY'
    """)
    blocked = cur.fetchone()[0]
    print(f"Blocked Safety: {blocked}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
