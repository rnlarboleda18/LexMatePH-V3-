import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def extract_ids():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Get ALL IDs where document_type is NULL
        # We assume valid full text check has been done (1257 of them)
        cur.execute("""
            SELECT id 
            FROM sc_decided_cases 
            WHERE document_type IS NULL
        """)
        
        rows = cur.fetchall()
        ids = [str(r[0]) for r in rows]
        
        with open("scripts/repair_ids.txt", "w") as f:
            f.write(",".join(ids))
            
        print(f"Extracted {len(ids)} IDs to scripts/repair_ids.txt")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_ids()
