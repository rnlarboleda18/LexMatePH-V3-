import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    try:
        print("Backfilling remaining untagged digests as 'gemini-3.0-flash'...")
        
        # User Logic: "yesterday I started a digest run using gemini 3.0 flash decending"
        # We assume ANY digested case that hasn't been tagged by our other scripts (which handle 
        # the specific 2.5-pro and 2.5-flash batches) belongs to this 3.0-flash run.
        
        cur.execute("""
            UPDATE sc_decided_cases 
            SET ai_model = 'gemini-3.0-flash' 
            WHERE digest_significance IS NOT NULL 
            AND ai_model IS NULL
        """)
        
        print(f"Updated {cur.rowcount} cases to 'gemini-3.0-flash'.")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
