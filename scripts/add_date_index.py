import os
import psycopg2

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

def add_date_index():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("Adding index on date column...")
        # IF NOT EXISTS is good practice
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sc_decided_cases_date ON sc_decided_cases(date);")
        print("Index idx_sc_decided_cases_date created/verified.")
        
    except Exception as e:
        print(f"Error adding index: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_date_index()
