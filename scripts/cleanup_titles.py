import os
import psycopg2

db_url = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

# Remove asterisks
cur.execute("""
    UPDATE sc_decided_cases
    SET short_title = TRIM(BOTH '*' FROM short_title)
    WHERE EXTRACT(YEAR FROM date) = 1901 AND short_title LIKE '%*%'
""")
print(f"Cleaned asterisks: {cur.rowcount} rows")

# Remove underscores
cur.execute("""
    UPDATE sc_decided_cases
    SET short_title = TRIM(BOTH '_' FROM short_title)
    WHERE EXTRACT(YEAR FROM date) = 1901 AND short_title LIKE '%_%'
""")
print(f"Cleaned underscores: {cur.rowcount} rows")

conn.close()
