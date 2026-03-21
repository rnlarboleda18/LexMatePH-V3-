import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Creating Full-Text Search Index (GIN)...")
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        conn.autocommit = True # Required for CREATE INDEX concurrently if we wanted, but standard is fine
        cur = conn.cursor()
        
        # We will index a concatenation of important text fields
        # This might take a while!
        sql = """
        CREATE INDEX IF NOT EXISTS idx_sc_decisions_fts_v1 
        ON sc_decided_cases 
        USING GIN (
            to_tsvector('english', 
                COALESCE(title, '') || ' ' || 
                COALESCE(short_title, '') || ' ' || 
                COALESCE(case_number, '') || ' ' || 
                COALESCE(main_doctrine, '') || ' ' || 
                COALESCE(full_text_md, '')
            )
        );
        """
        
        print("Executing CREATE INDEX... (This may take minutes)")
        cur.execute("SET statement_timeout = 0") # Disable timeout
        cur.execute(sql)
        print("Index Created Successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
