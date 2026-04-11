import os
import psycopg2

db_url = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Find a case in 1901-1903 NOT processed by the new model yet
cur.execute("""
    SELECT case_number, short_title, main_doctrine, ai_model, date
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1903
    AND (ai_model != 'gemini-2.5-flash-lite' OR ai_model IS NULL)
    LIMIT 1
""")
bad_row = cur.fetchone()

# Find a case that WAS processed
cur.execute("""
    SELECT case_number, short_title, main_doctrine, ai_model, date
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1903
    AND ai_model = 'gemini-2.5-flash-lite'
    LIMIT 1
""")
good_row = cur.fetchone()

print("--- UNPROCESSED CASE (Old/Missing Data) ---")
if bad_row:
    print(f"Case: {bad_row[0]} ({bad_row[4]})")
    print(f"Model: {bad_row[3]}")
    print(f"Short Title: {bad_row[1]}")
    print(f"Main Doctrine: {str(bad_row[2])[:50]}...")
else:
    print("None found (All processed?)")

print("\n--- PROCESSED CASE (New Data) ---")
if good_row:
    print(f"Case: {good_row[0]} ({good_row[4]})")
    print(f"Model: {good_row[3]}")
    print(f"Short Title: {good_row[1]}")
    print(f"Main Doctrine: {str(good_row[2])[:50]}...")
else:
    print("None found")

conn.close()
