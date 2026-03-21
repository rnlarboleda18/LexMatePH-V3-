import psycopg2
import os
import sys

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    if len(sys.argv) < 2:
        print("Usage: python lookup_case_id.py <ID>")
        return

    case_id = sys.argv[1]
    
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        cur.execute("SELECT id, case_number, title, date, digest_significance, digest_facts FROM supreme_decisions WHERE id = %s", (case_id,))
        result = cur.fetchone()
        
        if result:
            print(f"--- Case ID {case_id} ---")
            print(f"G.R. Number:  {result[1]}")
            print(f"Title:        {result[2]}")
            print(f"Date:         {result[3]}")
            print(f"Facts Len:    {len(result[5]) if result[5] else 'None'}")
            print(f"Significance: {result[4]}")
        else:
            print(f"Case ID {case_id} not found.")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
