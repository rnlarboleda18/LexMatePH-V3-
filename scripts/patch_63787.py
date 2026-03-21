import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Patching Case 63787 (G.R. Nos. 240209 & 240212)...")
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Values from my previous report
        case_no = "G.R. Nos. 240209 & 240212"
        date_str = "2023-01-10"
        
        cur.execute("""
            UPDATE sc_decided_cases 
            SET case_number = %s, date = %s 
            WHERE id = 63787
        """, (case_no, date_str))
        
        conn.commit()
        print("Update successful.")
        
        # Verify
        cur.execute("SELECT id, case_number, date FROM sc_decided_cases WHERE id = 63787")
        print(f"Verified: {cur.fetchone()}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
