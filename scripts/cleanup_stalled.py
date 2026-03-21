import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Resetting ALL 'PROCESSING' cases to NULL...")
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE sc_decided_cases 
            SET digest_significance = NULL 
            WHERE digest_significance = 'PROCESSING'
        """)
        
        count = cur.rowcount
        conn.commit()
        print(f"Released {count} stalled cases.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
