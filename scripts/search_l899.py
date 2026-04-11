import os
import psycopg2

db_url = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("""
    SELECT 
        case_number, ai_model, digest_facts
    FROM sc_decided_cases 
    WHERE case_number = 'G.R. No. L-899'
""")
row = cur.fetchone()
if row:
    print("Exact match 'G.R. No. L-899' found.")
    print(f"Model: {row[1]}")
    print(f"Facts present: {bool(row[2])}")
else:
    print("Exact match 'G.R. No. L-899' NOT found.")
    cur.execute("SELECT case_number FROM sc_decided_cases WHERE case_number ILIKE '%L-899%'")
    rows = cur.fetchall()
    print(f"Similar cases: {[r[0] for r in rows]}")

conn.close()
