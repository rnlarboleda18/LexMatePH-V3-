import os
import psycopg2

db_url = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

print("Resetting STUCK 'PROCESSING' cases (Updated > 30 mins ago)...")

cur.execute("""
    UPDATE sc_decided_cases 
    SET digest_significance = NULL 
    WHERE digest_significance LIKE '%PROCESSING%' 
      AND updated_at < NOW() - INTERVAL '30 minutes'
""")

print(f"Reset {cur.rowcount} stuck cases.")
conn.close()
