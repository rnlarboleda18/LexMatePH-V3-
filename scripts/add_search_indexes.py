import os
import psycopg2

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

def add_indexes():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("Adding index on case_number...")
        # IF NOT EXISTS is good practice to avoid errors if re-run
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sc_decided_cases_number ON sc_decided_cases(case_number);")
        print("Index idx_sc_decided_cases_number created/verified.")

        print("Adding GIN index on short_title (FTS)...")
        # Standard english configuration for title search
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sc_decided_cases_title_fts ON sc_decided_cases USING GIN (to_tsvector('english', COALESCE(short_title, '')));")
        print("Index idx_sc_decided_cases_title_fts created/verified.")
        
    except Exception as e:
        print(f"Error adding indexes: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_indexes()
