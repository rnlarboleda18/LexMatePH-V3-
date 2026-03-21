import os
import psycopg2

db_url = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"
conn = psycopg2.connect(db_url)
conn.autocommit = True # Required for CREATE INDEX CONCURRENTLY
cur = conn.cursor()

print("Creating pg_trgm extension...")
try:
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    print("Extension created (or already exists).")
except Exception as e:
    print(f"Error creating extension: {e}")

print("Creating GIN index on case_number (this may take a while)...")
try:
    cur.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_case_number_trgm ON sc_decided_cases USING GIN (case_number gin_trgm_ops);")
    print("Index created.")
except Exception as e:
    print(f"Error creating index: {e}")

# Optional: Index on Title too
print("Creating GIN index on title...")
try:
    cur.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_title_trgm ON sc_decided_cases USING GIN (title gin_trgm_ops);")
    print("Index created.")
except Exception as e:
    print(f"Error creating index: {e}")

conn.close()
